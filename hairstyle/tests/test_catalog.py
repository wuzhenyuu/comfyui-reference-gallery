import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('hairstyle_catalog',Path(__file__).resolve().parents[1]/'catalog.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=c.LIBRARY;self.old_user=c.USER_LIBRARY;c.LIBRARY=Path(self.tmp.name);c.USER_LIBRARY=c.LIBRARY/"user"
  self.row={'id':'h-f123','source_id':'f123','name_zh':'空气刘海短发','section':'hairstyle',**{field:f'img/{kind}/h-f123{suffix}' for kind,(field,suffix) in c.FIELDS.items()}}
  for kind,(field,suffix) in c.FIELDS.items():
   p=c.LIBRARY/self.row[field];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
  (c.LIBRARY/'data').mkdir();self.write([self.row])
 def write(self,rows):(c.LIBRARY/'data/hairstyle-zh.json').write_text(json.dumps(rows,ensure_ascii=False))
 def tearDown(self):c.LIBRARY=self.old;c.USER_LIBRARY=self.old_user;c._read_library.cache_clear();self.tmp.cleanup()
 def test_generated_images_are_allowlisted(self):
  for kind,(_,suffix) in c.FIELDS.items():self.assertEqual(c.asset(kind,'h-f123'+suffix).read_bytes(),b'fixture')
 def test_paths_extensions_and_unknown_ids_are_rejected(self):
  for kind,name in [('full','../h-f123.png'),('full','..\\h-f123.png'),('full','/etc/passwd'),('full','h-f123.webp'),('full','unknown.png'),('data','hairstyle-zh.json')]:
   with self.subTest(kind=kind,name=name),self.assertRaises(ValueError):c.asset(kind,name)
 def test_external_symlink_is_rejected(self):
  p=c.LIBRARY/self.row['full'];p.unlink();p.symlink_to('/etc/passwd')
  with self.assertRaises(ValueError):c.asset('full','h-f123.png')
 def test_index_reloads_after_new_generation(self):
  self.assertEqual(len(c.records()),1);self.write([dict(self.row,name_zh='更新名称')]);self.assertEqual(c.hairstyle('h-f123')['name_zh'],'更新名称')
 def test_invalid_and_duplicate_records_are_rejected(self):
  for rows in [[self.row,self.row],[dict(self.row,full='../secret.png')],[dict(self.row,name_zh='')],[dict(self.row,section='face')]]:
   self.write(rows)
   with self.assertRaises(ValueError):c.records()
 def test_missing_file_has_guidance(self):
  (c.LIBRARY/self.row['full']).unlink()
  with self.assertRaisesRegex(FileNotFoundError,'完整'):c.asset('full','h-f123.png')
if __name__=='__main__':unittest.main()
