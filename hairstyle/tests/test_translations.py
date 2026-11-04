import importlib.util,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('translated_catalog',ROOT/'catalog.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class TranslationTests(unittest.TestCase):
 def test_runtime_dictionary_contains_valid_translations(self):
  self.assertTrue(c.NAME_EN)
  for source,english in c.NAME_EN.items():
   self.assertIsInstance(source,str);self.assertTrue(source);self.assertIsInstance(english,str);self.assertTrue(english);self.assertNotRegex(english,r'[\u3400-\u9fff]')
 @unittest.skipUnless((c.LIBRARY/c.INDEX_FILE).is_file(),'Optional installed hairstyle library is not present')
 def test_all_bundled_names_have_english_translations_and_keep_source_fields(self):
  raw=json.loads((c.LIBRARY/'data/hairstyle-zh.json').read_text());rows=[row for row in c.records() if row["origin"]=="builtin"];self.assertEqual(len(rows),len(raw))
  for source,row in zip(raw,rows):
   with self.subTest(id=row['id']):
    self.assertIn(source['name_zh'],c.NAME_EN)
    self.assertTrue(row['name_en']);self.assertFalse(re.search('[\u4e00-\u9fff]',row['name_en']))
    self.assertEqual(row['name_zh'],source['name_zh']);self.assertEqual(row['name_ja'],source['name_ja'])
    self.assertIn(row['name_en'].lower(),row['search'])
 @unittest.skipUnless((c.LIBRARY/c.INDEX_FILE).is_file(),'Optional installed hairstyle library is not present')
 def test_english_search_and_chinese_search_agree_for_above_brow_bangs(self):
  rows=[row for row in c.records() if row["origin"]=="builtin"];en=[r['id'] for r in rows if 'above-brow' in r['search']];zh=[r['id'] for r in rows if '眉上齐刘海' in r['name_zh']]
  self.assertEqual(set(en),set(zh));self.assertEqual(len(en),38)
if __name__=='__main__':unittest.main()
