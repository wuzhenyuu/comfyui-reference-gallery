"""Run with ComfyUI's Python to exercise real image tensors and random outputs."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class RandomNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec('torch') is None:
            raise unittest.SkipTest('Run these tensor tests with the ComfyUI Python interpreter')
        from aiohttp import web
        spec=importlib.util.spec_from_file_location('hairstyle_random_tests',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
        server=types.ModuleType('server');server.PromptServer=types.SimpleNamespace(instance=types.SimpleNamespace(routes=web.RouteTableDef()))
        previous_server=sys.modules.get('server');sys.modules['server']=server
        try:spec.loader.exec_module(module)
        finally:
            if previous_server is None:sys.modules.pop('server',None)
            else:sys.modules['server']=previous_server
        cls.module=module;cls.catalog=sys.modules[spec.name+'.catalog'];cls.node=module.RandomHairstyleGallery
    def setUp(self):
        from PIL import Image
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.old,self.old_user=self.catalog.LIBRARY,self.catalog.USER_LIBRARY
        self.catalog.LIBRARY,self.catalog.USER_LIBRARY=self.root/'builtin',self.root/'user'
        self.builtin={'id':'h-original','section':'hairstyle','section_zh':'假人发型','name_zh':'短发发型','title':'短发发型','name_ja':'','style':'','style_zh':'','hair':'ショート','hair_zh':'短发','source_id':'original','w':8,'h':12,'bytes':0,'full':'img/full/h-original.png','preview':'img/preview/h-original.webp','thumb':'img/thumb/h-original.webp'}
        index=self.catalog.LIBRARY/'data/hairstyle-zh.json';index.parent.mkdir(parents=True);index.write_text(json.dumps([self.builtin]))
        full=self.catalog.LIBRARY/self.builtin['full'];full.parent.mkdir(parents=True);Image.new('RGB',(8,12),'red').save(full)
        out=BytesIO();Image.new('RGB',(10,14),'blue').save(out,format='PNG')
        self.custom=self.module.import_image(out.getvalue(),name='自定义蓝发',other_name='My blue hair',filename='hair.png',root=self.catalog.USER_LIBRARY)
    def tearDown(self):
        self.catalog.LIBRARY,self.catalog.USER_LIBRARY=self.old,self.old_user;self.catalog._read_library.cache_clear();self.temp.cleanup()
    def test_sources_skip_missing_originals_and_support_custom_only_library(self):
        self.assertEqual({r['id'] for r in self.node._candidates()},{self.builtin['id'],self.custom['id']})
        self.assertEqual(self.node._candidates('builtin')[0]['id'],self.builtin['id'])
        self.assertEqual(self.node._candidates('user')[0]['id'],self.custom['id'])
        (self.catalog.LIBRARY/self.builtin['full']).unlink()
        self.assertEqual([r['id'] for r in self.node._candidates()],[self.custom['id']])
        (self.catalog.LIBRARY/'data/hairstyle-zh.json').unlink()
        self.assertIs(self.node.VALIDATE_INPUTS(),True)
    def test_empty_or_invalid_sources_produce_readable_validation_errors(self):
        self.assertIn('无效',self.node.VALIDATE_INPUTS('invalid'))
        (self.catalog.USER_LIBRARY/self.custom['full']).unlink()
        self.assertIn('没有可用',self.node.VALIDATE_INPUTS('user'))
        self.assertIn('No available',self.node.VALIDATE_INPUTS('user','en'))
        with self.assertRaises(ValueError):self.node().load_random('user')
    def test_each_call_resamples_and_all_eight_outputs_match_one_actual_reference(self):
        choices=[self.custom,self.builtin,self.custom]
        with patch.object(self.module.random,'choice',side_effect=choices) as choose:
            results=[self.node().load_random(language='en') for _ in range(3)]
        self.assertEqual(choose.call_count,3)
        for item,chosen in zip(results,choices):
            result=item['result'];self.assertEqual(len(result),8);self.assertEqual(result[3],chosen['id'])
            self.assertEqual(result[0].shape,(1,chosen['h'],chosen['w'],3));self.assertEqual(result[1:3],(chosen['w'],chosen['h']))
            row=self.catalog.hairstyle(chosen['id']);self.assertEqual(result[4],row['name_en']);self.assertEqual(result[6],row['hair_en']);self.assertEqual(result[7],row['source_id'])
            self.assertEqual(item['ui']['hairstyle_id'],[chosen['id']]);self.assertEqual(item['ui']['name'],[result[4]])
            rgb=result[0][0,0,0].tolist();self.assertEqual(rgb,[0.0,0.0,1.0] if chosen is self.custom else [1.0,0.0,0.0])
    def test_fresh_fingerprint_is_json_safe_and_original_node_stays_fixed(self):
        values=[self.node.IS_CHANGED() for _ in range(4)];self.assertEqual(len(set(values)),4);json.dumps(values,allow_nan=False)
        old=self.module.HairstyleGallery
        self.assertEqual(set(old.INPUT_TYPES()['required']),{'hairstyle_id'});self.assertEqual(set(old.INPUT_TYPES()['optional']),{'language'})
        self.assertEqual(old.IS_CHANGED(self.builtin['id']),old.IS_CHANGED(self.builtin['id']))
        first=old().load_hairstyle(self.builtin['id']);second=old().load_hairstyle(self.builtin['id'])
        self.assertIsInstance(first,tuple);self.assertEqual(first[3:],second[3:]);self.assertTrue(first[0].equal(second[0]));self.assertEqual(self.node.RETURN_NAMES,old.RETURN_NAMES)

    def test_existing_name_socket_and_other_text_outputs_follow_language(self):
        node=self.module.HairstyleGallery
        self.assertEqual(node.RETURN_NAMES,('image','width','height','hairstyle_id','name','description','hair_length','source_id'))
        for load in (lambda lang:node().load_hairstyle(self.builtin['id'],lang),lambda lang:self.node().load_random('builtin',lang)['result']):
            zh,en=load('zh'),load('en')
            self.assertEqual(en[4],'Short hairstyle');self.assertEqual(zh[4],'短发发型')
            for index in (4,5,6):self.assertNotRegex(en[index],r'[\u3400-\u9fff]')
            self.assertEqual(len(en),8);self.assertEqual(zh[1:4],en[1:4]);self.assertTrue(zh[0].equal(en[0]))
        self.assertEqual(node().load_hairstyle(self.custom['id'],'en')[4],'My blue hair')



    def test_locked_selection_preserves_all_outputs_without_resampling(self):
        fixed = self.module.HairstyleGallery
        identity = self.custom['id']
        inputs = dict(origin='builtin', language='en', hairstyle_id=identity, locked=True)

        with patch.object(self.module.random, 'choice', side_effect=AssertionError('Locked selection must not draw')):
            self.assertIs(self.node.VALIDATE_INPUTS(**inputs), True)
            result = [self.node().load_random(**inputs) for _ in range(3)]
            fingerprint = self.node.IS_CHANGED(**inputs)
            self.assertEqual(fingerprint, self.node.IS_CHANGED(**inputs))
        expected = fixed().load_hairstyle(identity, 'en')
        for item in result:
            self.assertTrue(item['result'][0].equal(expected[0]))
            self.assertEqual(item['result'][1:], expected[1:])
            self.assertEqual(item['ui']['hairstyle_id'], [identity])
        self.assertNotEqual(fingerprint, self.node.IS_CHANGED(**dict(inputs, language='zh')))
        from PIL import Image
        Image.new('RGB', (10, 14), 'green').save(self.catalog.USER_LIBRARY / self.custom['full'])
        self.assertNotEqual(fingerprint, self.node.IS_CHANGED(**inputs))
        with patch.object(self.module.random, 'choice', return_value=self.builtin) as choose:
            self.assertEqual(self.node().load_random(hairstyle_id=identity)['result'][3], self.builtin['id'])
            choose.assert_called_once()

    def test_missing_locked_images_fail_without_drawing_replacements(self):
        with patch.object(self.module.random, 'choice', side_effect=AssertionError('Must not draw')):
            self.assertIn('先点击骰子', self.node.VALIDATE_INPUTS(locked=True))
            with self.assertRaises(ValueError):
                self.node().load_random(locked=True)
            identity = self.custom['id']
            (self.catalog.USER_LIBRARY / self.custom['full']).unlink()
            self.assertIsNot(self.node.VALIDATE_INPUTS(hairstyle_id=identity, locked=True), True)
            with self.assertRaises((ValueError, FileNotFoundError)):
                self.node().load_random(hairstyle_id=identity, locked=True)

    def test_dice_http_filters_and_no_repeat_never_load_image_tensors(self):
        import asyncio
        async def scenario():
            from aiohttp import web
            from aiohttp.test_utils import TestClient, TestServer
            app = web.Application()
            app.add_routes(self.module.routes)
            fixed = self.module.HairstyleGallery
            with patch.object(fixed, 'load_hairstyle', side_effect=AssertionError('Dice must not load image tensors')):
                async with TestClient(TestServer(app)) as client:
                    response = await client.get('/hairstyle_gallery/random', params={'exclude_id': self.builtin['id'], 'language': 'en'})
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    data = await response.json()
                    self.assertEqual(data['hairstyle_id'], self.custom['id'])
                    self.assertEqual(data['name'], self.custom['name_en'])
                    response = await client.get('/hairstyle_gallery/random', params={'origin': 'builtin', 'exclude_id': self.builtin['id']})
                    self.assertEqual(response.status, 200)
                    self.assertEqual((await response.json())['hairstyle_id'], self.builtin['id'])
                    response = await client.get('/hairstyle_gallery/random', params={'origin': 'bad'})
                    self.assertEqual(response.status, 400)
                    self.assertIn('error', await response.json())

        asyncio.run(scenario())

    def test_cleaned_originals_cannot_reenter_the_random_pool(self):
        for state in ('thumb_only', 'removed'):
            row = dict(self.catalog.hairstyle(self.builtin['id']), management_state=state)
            with patch.object(self.module, 'records', return_value=[row]):
                with self.assertRaises(ValueError):
                    self.node._candidates('builtin')

    def test_packaged_static_routes_resolve_nested_frontend(self):
        import asyncio
        from aiohttp import web
        expected = ROOT.parent / 'web' / 'hairstyle'
        self.assertEqual(self.module.WEB_ROOT, expected)
        self.assertEqual(set(self.module.NODE_CLASS_MAPPINGS), {'HairstyleGallery', 'RandomHairstyleGallery'})
        response = asyncio.run(self.module.gallery_route(None))
        self.assertEqual(response._path, expected / 'gallery.html')
        self.assertTrue(response._path.is_file())
        for name in ('style.css', 'core.mjs', 'app.mjs', 'i18n.mjs', 'icon.svg', 'library_manager.mjs', 'library_manager.css', 'asset_editor.mjs'):
            with self.subTest(name=name):
                response = asyncio.run(self.module.ui_route(types.SimpleNamespace(match_info={'filename': name})))
                self.assertEqual(response._path, expected / name)
                self.assertTrue(response._path.is_file())
        with self.assertRaises(web.HTTPNotFound):
            asyncio.run(self.module.ui_route(types.SimpleNamespace(match_info={'filename': '../__init__.py'})))
        for name in ('hairstyle_gallery.js', 'random_hairstyle_gallery.js'):
            source = (expected / name).read_text(encoding='utf-8')
            self.assertIn('"../../../scripts/app.js"', source)
            self.assertIn('"../../../scripts/api.js"', source)


if __name__=='__main__':unittest.main()
