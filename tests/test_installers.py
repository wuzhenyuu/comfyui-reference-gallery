"""Offline installer regressions using temporary fixtures, never the user's library."""
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install_libraries as common
import install_costume_library as costume
import install_pose_library as pose


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def image(self, relative, format):
        output = BytesIO()
        Image.new("RGB", (2, 3), "red").save(output, format=format)
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(output.getvalue())
        return path

    def make_costume(self):
        source = {"url": costume.SOURCE_URL, "commit": costume.COMMIT,
                  "keyword_translations": {f"word{i}": f"词{i}" for i in range(87)},
                  "search_aliases": {f"别名{i}": f"word{i}" for i in range(79)}}
        items = []
        for library in ("real", "anime"):
            identity = "SPR-0001"
            item = {"id": f"{library}:{identity}", "source_id": identity, "library": library,
                    "category": "spring", "category_zh": "春", "category_en": "Spring",
                    "keywords_en": "red dress", "keywords_zh": "红 连衣裙",
                    "image": f"{library}/img/{identity}.webp", "thumbnail": f"{library}/thumbs/{identity}.webp"}
            for field in ("image", "thumbnail"):
                self.image(item[field], "WEBP")
            items.append(item)
        payload = {"schema_version": 1, "source": source, "items": items}
        (self.source / "catalog.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def make_pose(self):
        row = {"id": "pose_front", "体系": "全身单人", "姿势编号": "P001", "分类": "站姿",
               "姿势名称": "站立", "角度": "正面", "检索": "站立 正面",
               "原图": "img/pose_front.png", "缩略图": "thumbs/pose_front.jpg"}
        (self.source / "data").mkdir()
        (self.source / "data/pose-zh.json").write_text(json.dumps([row], ensure_ascii=False), encoding="utf-8")
        (self.source / "data/meta-zh.json").write_text(json.dumps({"体系分类": ["全身单人"]}, ensure_ascii=False), encoding="utf-8")
        (self.source / "SOURCE.json").write_text(json.dumps({"url": pose.SOURCE_URL, "revision": pose.COMMIT, "images": 1}))
        (self.source / "LICENSE").write_bytes((ROOT / "sources/pose/LICENSE.upstream.txt").read_bytes())
        (self.source / "README.md").write_text("Upstream fixture", encoding="utf-8")
        self.image(row["原图"], "PNG")
        self.image(row["缩略图"], "JPEG")
        return row

    def run_costume(self):
        with patch.object(costume, "COUNTS", {"real": 1, "anime": 1}), patch.object(common, "download", side_effect=AssertionError("offline source must never download")):
            return costume.run(self.source, self.target)

    def run_pose(self):
        with patch.object(pose, "EXPECTED_RECORDS", 1), patch.object(common, "download", side_effect=AssertionError("offline source must never download")):
            return pose.run(self.source, self.target)

    def test_costume_offline_count_whitelist_and_rerun_preserve_unrelated(self):
        self.make_costume()
        (self.source / "private.txt").write_text("not part of a library")
        self.target.mkdir()
        (self.target / "keep.txt").write_text("user file")
        report = self.run_costume()
        self.assertEqual((report["records"], report["images"]), (2, 4))
        self.assertEqual(len(list(self.target.rglob("*.webp"))), 4)
        self.assertFalse((self.target / "private.txt").exists())
        image = self.target / "real/img/SPR-0001.webp"
        before = image.stat().st_mtime_ns
        self.run_costume()
        self.assertEqual(image.stat().st_mtime_ns, before)
        self.assertEqual((self.target / "keep.txt").read_text(), "user file")

    def test_pose_offline_installs_only_referenced_chinese_metadata_and_images(self):
        self.make_pose()
        (self.source / "data/private.json").write_text("{}")
        self.image("img/unreferenced.png", "PNG")
        report = self.run_pose()
        self.assertEqual((report["records"], report["images"]), (1, 2))
        self.assertFalse((self.target / "data/private.json").exists())
        self.assertFalse((self.target / "img/unreferenced.png").exists())
        self.assertEqual(json.loads((self.target / "SOURCE.json").read_text())["revision"], pose.COMMIT)
        self.assertEqual((self.target / "LICENSE").read_bytes(), (self.source / "LICENSE").read_bytes())

    def test_installed_revision_mismatch_rejected_without_publication(self):
        payload = self.make_costume()
        payload["source"]["commit"] = "HEAD"
        (self.source / "catalog.json").write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "pinned"):
            self.run_costume()
        self.assertFalse(self.target.exists())

    def test_record_count_mismatch_is_not_accepted(self):
        self.make_costume()
        with patch.object(costume, "COUNTS", {"real": 2, "anime": 1}), self.assertRaisesRegex(ValueError, "counts"):
            costume.run(self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_invalid_asset_path_rejected_before_publication(self):
        payload = self.make_costume()
        payload["items"][0]["image"] = "../private.webp"
        (self.source / "catalog.json").write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "asset path"):
            self.run_costume()
        self.assertFalse(self.target.exists())

    def test_corrupt_image_keeps_existing_index_and_files(self):
        self.make_costume()
        self.target.mkdir()
        old_index = b"existing catalog must not be replaced"
        (self.target / "catalog.json").write_bytes(old_index)
        (self.source / "anime/thumbs/SPR-0001.webp").write_bytes(b"bad image")
        with self.assertRaisesRegex(ValueError, "WebP"):
            self.run_costume()
        self.assertEqual((self.target / "catalog.json").read_bytes(), old_index)
        self.assertEqual(list(self.target.iterdir()), [self.target / "catalog.json"])

    def test_publication_error_never_replaces_index(self):
        self.make_costume()
        self.target.mkdir()
        (self.target / "catalog.json").write_bytes(b"old index")
        original = common.atomic_write
        def fail_image(path, content):
            if path.is_relative_to(self.target.resolve()):
                raise OSError("simulated disk error")
            return original(path, content)
        with patch.object(common, "atomic_write", side_effect=fail_image), self.assertRaisesRegex(OSError, "disk error"):
            self.run_costume()
        self.assertEqual((self.target / "catalog.json").read_bytes(), b"old index")

    def test_user_managed_destination_is_rejected(self):
        self.make_pose()
        (self.target / "data").mkdir(parents=True)
        (self.target / "data/custom.json").write_text("[]")
        with self.assertRaisesRegex(ValueError, "user-managed"):
            self.run_pose()
        with patch.dict(os.environ, {"COMFYUI_POSE_GALLERY_USER_LIBRARY": str(self.root)}), self.assertRaisesRegex(ValueError, "overlaps"):
            common.check_destination(self.target, "COMFYUI_POSE_GALLERY_USER_LIBRARY")

    def test_path_and_source_symlink_escape_is_rejected(self):
        for value in ("../outside", "/absolute", "C:/absolute", "a\\b", "a//b", "a/./b"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                common.safe_path(self.source, value)
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret").write_text("private")
        try:
            (self.source / "link").symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(str(error))
        with self.assertRaisesRegex(ValueError, "escapes"):
            common.DirectorySource(self.source).read("link/secret")
        with self.assertRaisesRegex(ValueError, "escapes"):
            common.publish(self.source, self.source, ["link/secret"], "link/secret")

    def test_zip_reader_uses_whitelist_and_rejects_duplicate_members(self):
        archive = self.root / "source.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("pin/allowed.txt", "allowed")
            zipped.writestr("pin/../../escape", "unread")
        with zipfile.ZipFile(archive) as zipped:
            reader = common.ZipSource(zipped, "pin/")
            self.assertEqual(reader.read("allowed.txt"), b"allowed")
            with self.assertRaises(ValueError):
                reader.read("../../escape")
            with self.assertRaises(ValueError):
                reader.read("allowed.txt", 1)
        self.assertFalse((self.root / "escape").exists())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "a") as zipped:
                zipped.writestr("pin/allowed.txt", "duplicate")
        with zipfile.ZipFile(archive) as zipped, self.assertRaisesRegex(ValueError, "duplicate"):
            common.ZipSource(zipped, "pin/").read("allowed.txt")

    def test_pose_pinned_zip_path_works_without_extracting_other_files(self):
        self.make_pose()
        archive = self.root / "pose.zip"
        prefix = f"ai-pose-gallery-zh-{pose.COMMIT}/"
        with zipfile.ZipFile(archive, "w") as zipped:
            for path in self.source.rglob("*"):
                if path.is_file():
                    zipped.write(path, prefix + path.relative_to(self.source).as_posix())
            zipped.writestr(prefix + "scripts/untrusted.py", "raise RuntimeError('must not run')")
            zipped.writestr(prefix + "../../escape", "must not extract")
        with patch.object(pose, "EXPECTED_RECORDS", 1), patch.object(common, "download", side_effect=AssertionError("offline ZIP")):
            report = pose.run(destination=self.target, archive=archive)
        self.assertEqual(report["images"], 2)
        self.assertFalse((self.target / "scripts").exists())
        self.assertFalse((self.root / "escape").exists())

    def test_costume_pinned_zip_imports_both_json_arrays_and_static_dictionaries(self):
        payload = self.make_costume()
        archive = self.root / "costume.zip"
        prefix = f"nvzhuang-{costume.COMMIT}/"
        def javascript_dictionary(name, values):
            return "const " + name + " = {" + ",".join(f"'{k}':'{v}'" for k, v in values.items()) + "};"
        frontend = javascript_dictionary("EN2ZH", payload["source"]["keyword_translations"]) + javascript_dictionary("ZH_ALIAS", payload["source"]["search_aliases"])
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr(prefix + "index.html", frontend)
            zipped.writestr(prefix + "LICENSE", (ROOT / "sources/costume/LICENSE.upstream.txt").read_bytes())
            for item in payload["items"]:
                library = item["library"]
                source_prefix = "anime/" if library == "anime" else ""
                row = {"id": item["source_id"], "カテゴリ": "春", "キーワード": item["keywords_en"],
                       "サムネ": source_prefix + "thumbs/SPR-0001.webp", "画像": source_prefix + "img/SPR-0001.webp", "原寸": "not-downloaded.png"}
                filename, variable = ("data-anime.js", "D_ANIME") if library == "anime" else ("data.js", "D")
                zipped.writestr(prefix + filename, f"const {variable} = {json.dumps([row], ensure_ascii=False)};")
                for field, original_field in (("image", "画像"), ("thumbnail", "サムネ")):
                    zipped.writestr(prefix + "assets/" + row[original_field], (self.source / item[field]).read_bytes())
            zipped.writestr(prefix + "backend/main.go", "not installed or executed")
        with patch.object(costume, "COUNTS", {"real": 1, "anime": 1}), patch.object(common, "download", side_effect=AssertionError("offline ZIP")):
            report = costume.run(destination=self.target, archive=archive)
        self.assertEqual(report["images"], 4)
        self.assertFalse((self.target / "backend").exists())
        catalog = json.loads((self.target / "catalog.json").read_text("utf-8"))
        self.assertEqual(catalog["source"]["keyword_translations"], payload["source"]["keyword_translations"])

    def test_image_format_checks_reject_truncation_and_crc_changes(self):
        png = self.image("test.png", "PNG").read_bytes()
        jpeg = self.image("test.jpg", "JPEG").read_bytes()
        webp = self.image("test.webp", "WEBP").read_bytes()
        self.assertEqual(common.validate_png(png), (2, 3))
        self.assertEqual(common.validate_jpeg(jpeg), (2, 3))
        self.assertEqual(costume.webp_dimensions(webp), (2, 3))
        for validate, content in ((common.validate_png, png), (common.validate_jpeg, jpeg), (costume.webp_dimensions, webp)):
            with self.subTest(format=validate.__name__), self.assertRaises(ValueError):
                validate(content[:-1])
        changed = bytearray(png)
        changed[20] ^= 1
        with self.assertRaisesRegex(ValueError, "CRC"):
            common.validate_png(changed)

    def test_js_dictionary_is_parsed_not_executed(self):
        self.assertEqual(costume.parse_dictionary("const EN2ZH = {'dress':'连衣裙',};", "EN2ZH", 1), {"dress": "连衣裙"})
        with self.assertRaises(ValueError):
            costume.parse_dictionary("const EN2ZH = {'dress':fetch('https://example.test')};", "EN2ZH", 1)


if __name__ == "__main__":
    unittest.main()
