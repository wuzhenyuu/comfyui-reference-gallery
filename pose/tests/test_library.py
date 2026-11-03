"""Guard against publishing a browsable gallery with no loadable originals."""
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]

class BundledLibraryTests(unittest.TestCase):
    def test_every_catalog_pose_has_an_original_and_thumbnail(self):
        library = ROOT / 'library'
        if not (library / 'data/pose-zh.json').is_file():
            self.skipTest('Install the optional pose library to check upstream image completeness')
        rows = json.loads((library / 'data/pose-zh.json').read_text(encoding='utf-8'))
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(pose=row['id']):
                original = library / row['原图']
                thumbnail = library / row['缩略图']
                with original.open('rb') as handle:
                    header = handle.read(24)
                self.assertEqual(header[:8], b'\x89PNG\r\n\x1a\n')
                self.assertEqual(struct.unpack('>II', header[16:24]), (900, 1200))
                with thumbnail.open('rb') as handle:
                    self.assertEqual(handle.read(2), b'\xff\xd8')

if __name__ == '__main__':
    unittest.main()
