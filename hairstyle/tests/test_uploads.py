import concurrent.futures
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj
u = module('hairstyle_uploads', 'uploads.py')
c = module('hairstyle_upload_catalog', 'catalog.py')


def picture(fmt='PNG', size=(80, 120), **kwargs):
    out = BytesIO()
    Image.new('RGB', size, '#965b45').save(out, format=fmt, **kwargs)
    return out.getvalue()


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'custom'
        self.old, self.old_user = c.LIBRARY, c.USER_LIBRARY
        c.LIBRARY, c.USER_LIBRARY = Path(self.temp.name) / 'missing-builtins', self.root
    def tearDown(self):
        c.LIBRARY, c.USER_LIBRARY = self.old, self.old_user
        c._read_library.cache_clear()
        self.temp.cleanup()
    def upload(self, data=None, **kwargs):
        return u.import_image(picture() if data is None else data,
            root=self.root, name=kwargs.pop('name', '自定义 <波波> & "刘海"'),
            filename=kwargs.pop('filename', '发型.png'), **kwargs)
    def test_formats_derivatives_bilingual_names_and_persistent_catalog(self):
        for fmt, ext in [('PNG', '.png'), ('JPEG', '.jpg'), ('WEBP', '.webp')]:
            row = self.upload(picture(fmt, (1200, 1600)), filename='发型'+ext, other_name='Custom bob', hair='short')
            self.assertRegex(row['id'], r'^u-[a-f0-9]{32}$')
            self.assertEqual(row['source_id'], '')
            with Image.open(self.root/row['full']) as full:
                self.assertEqual(full.format, 'PNG');self.assertEqual(full.size, (1200,1600))
            for kind, limit in [('preview',(800,1000)),('thumb',(400,500))]:
                with Image.open(self.root/row[kind]) as im:
                    self.assertLessEqual(im.width,limit[0]);self.assertLessEqual(im.height,limit[1])
                    self.assertAlmostEqual(im.width/im.height,.75,delta=.005)
        c._read_library.cache_clear()
        self.assertEqual(len(c.records()),3)
        saved=c.hairstyle(row['id'])
        self.assertEqual(saved['name_en'],'Custom bob')
        self.assertEqual(saved['name_zh'],'自定义 <波波> & "刘海"')
        self.assertEqual(c.asset('full',row['id']+'.png'),self.root/row['full'])
        meta=c.browser_payload()['meta']
        self.assertEqual((meta['builtin_count'],meta['user_count'],meta['builtin_missing']),(0,3,True))
    def test_custom_name_does_not_use_fixed_translation_and_english_primary_falls_back(self):
        row=self.upload(name='迷你波波（眉上齐刘海）')
        self.assertEqual(c.hairstyle(row['id'])['name_en'],row['name_zh'])
        row=self.upload(name='My own hairstyle',language='en')
        item=c.hairstyle(row['id'])
        self.assertEqual(item['name_zh'],'My own hairstyle')
        self.assertEqual((item['hair_zh'],item['hair_en']),('未分类','Unspecified'))
        self.assertIn('my own hairstyle',item['search'])
    def test_transparency_and_exif_orientation(self):
        out=BytesIO();Image.new('RGBA',(10,20),(0,0,0,0)).save(out,format='PNG')
        row=self.upload(out.getvalue())
        with Image.open(self.root/row['full']) as im:self.assertEqual(im.getpixel((0,0))[3],0)
        with Image.open(self.root/row['thumb']) as im:self.assertTrue(all(v>=250 for v in im.getpixel((0,0))))
        exif=Image.Exif();exif[274]=6
        row=self.upload(picture('JPEG',(30,50),exif=exif))
        self.assertEqual((row['w'],row['h']),(50,30))
    def test_invalid_content_size_metadata_and_paths_leave_no_assets(self):
        cases=[(b'not an image',{},'invalid_image'),(b'x'*(u.MAX_BYTES+1),{},'file_too_large'),
               (picture('GIF'),{},'unsupported_format'),(picture(),{'name':''},'name_required'),
               (picture(),{'name':'x'*121},'invalid_metadata'),(picture(),{'hair':'bad'},'invalid_metadata'),
               (picture(),{'filename':'../escape.png'},'invalid_filename'),
               (picture(),{'filename':'C:\\escape.png'},'invalid_filename')]
        for data,kwargs,error in cases:
            with self.subTest(error=error),self.assertRaises(u.UploadError) as caught:self.upload(data,**kwargs)
            self.assertEqual(caught.exception.code,error)
        self.assertFalse(self.root.exists())
    def test_animated_and_oversized_pixel_images_are_rejected_before_decoding(self):
        out=BytesIO();Image.new('RGB',(2,2),'red').save(out,format='PNG',save_all=True,append_images=[Image.new('RGB',(2,2),'blue')])
        with self.assertRaises(u.UploadError) as caught:self.upload(out.getvalue())
        self.assertEqual(caught.exception.code,'animated_image')
        data=bytearray(picture(size=(1,1)))
        data[16:24]=struct.pack('>II',8000,4001)
        data[29:33]=struct.pack('>I',zlib.crc32(data[12:29]))
        with self.assertRaises(u.UploadError) as caught:self.upload(bytes(data))
        self.assertEqual(caught.exception.code,'too_many_pixels')
    def test_concurrent_uploads_do_not_lose_index_records(self):
        self.root.mkdir(parents=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            rows=list(pool.map(lambda i:self.upload(name=f'Name {i}'),range(8)))
        index=json.loads((self.root/'data/custom.json').read_text())
        self.assertEqual(len(index),8);self.assertEqual({r['id'] for r in rows},{r['id'] for r in index})
        for row in rows:
            for kind in c.FIELDS:self.assertTrue((self.root/row[kind]).is_file())
    def test_index_commit_failure_rolls_back_only_the_new_files(self):
        first=self.upload();before=(self.root/'data/custom.json').read_bytes();replace=u.os.replace
        def fail_index(src,dst):
            if Path(dst).name=='custom.json':raise OSError('simulated disk error')
            return replace(src,dst)
        with patch.object(u.os,'replace',side_effect=fail_index):
            with self.assertRaises(u.UploadError) as caught:self.upload(name='Failed upload')
        self.assertEqual(caught.exception.code,'storage_error')
        self.assertEqual((self.root/'data/custom.json').read_bytes(),before)
        self.assertEqual(len(list((self.root/'img/full').glob('*'))),1)
        self.assertTrue((self.root/first['full']).exists())
        self.assertFalse(list(self.root.glob('.upload-*')))
        self.assertFalse(list((self.root/'data').glob('*.tmp')))
        self.upload(name='Successful retry')
        self.assertEqual(len(json.loads((self.root/'data/custom.json').read_text())),2)
    def test_external_write_and_read_symlinks_are_rejected(self):
        self.root.mkdir();outside=Path(self.temp.name)/'outside';outside.mkdir()
        (self.root/'img').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(u.UploadError):self.upload()
        self.assertFalse(list(outside.rglob('*')))
        (self.root/'img').unlink()
        row=self.upload();path=self.root/row['full'];path.unlink();path.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):c.asset('full',row['id']+'.png')
    def test_corrupt_index_is_not_overwritten(self):
        self.upload();path=self.root/'data/custom.json';path.write_text('{broken')
        with self.assertRaises(u.UploadError):self.upload()
        self.assertEqual(path.read_text(),'{broken')
        self.assertEqual(len(list((self.root/'img/full').glob('*'))),1)

if __name__=='__main__':unittest.main()
