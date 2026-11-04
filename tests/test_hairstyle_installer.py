"""Pinned, offline hairstyle installer checks using small temporary Git fixtures."""
from contextlib import ExitStack, redirect_stdout
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install_libraries as common
import install_hairstyle_library as hair
import install_pose_library as pose
import install_costume_library as costume


class HairstyleInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.clone, self.target = self.root / "upstream", self.root / "target"
        self.clone.mkdir()
        self.library = self.clone / "library"
        self.row = {"id": "h-fixture", "section": "hairstyle", "name_zh": "短发", "w": 2, "h": 3}
        trees = {kind: {} for kind in hair.KINDS}
        for kind, suffix in hair.KINDS.items():
            relative = f"img/{kind}/h-fixture{suffix}"
            self.row[kind] = relative
            output = BytesIO()
            Image.new("RGB", (2, 3), "red").save(output, format="PNG" if kind == "full" else "WEBP")
            content = output.getvalue()
            path = self.library / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            trees[kind][path.name] = hair.git_object("blob", content)
            if kind == "full":
                self.row["sha256"] = hashlib.sha256(content).hexdigest()
        self.write_rows([self.row])
        self.notices = {"LICENSE.upstream.txt": b"MIT License fixture\n", "THIRD_PARTY_NOTICES.md": b"Image source fixture\n"}
        for target, content in self.notices.items():
            (self.clone / ("LICENSE" if target == "LICENSE.upstream.txt" else target)).write_bytes(content)
        (self.clone / "untrusted.py").write_text("raise RuntimeError('must never execute')", encoding="utf-8")
        self.git("init", "--quiet")
        self.git("-c", "core.autocrlf=false", "add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "fixture")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.addCleanup(self.temporary.cleanup)
        for name, value in {"COMMIT": self.commit, "EXPECTED_RECORDS": 1,
                            "INDEX_SHA256": hashlib.sha256((self.library / hair.INDEX).read_bytes()).hexdigest(),
                            "IMAGE_TREES": {kind: hair.image_tree(blobs) for kind, blobs in trees.items()},
                            "NOTICE_HASHES": {name: hashlib.sha256(data).hexdigest() for name, data in self.notices.items()}}.items():
            self.patches.enter_context(patch.object(hair, name, value))
        self.patches.enter_context(patch.object(common, "download", side_effect=AssertionError("Offline fixtures must not download")))

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.clone), *args], text=True)

    def write_rows(self, rows):
        path = self.library / hair.INDEX
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    def run_install(self, **kwargs):
        return hair.run(source=kwargs.pop("source", self.clone), destination=kwargs.pop("destination", self.target), **kwargs)

    def test_clone_with_unrelated_edits_installs_only_allowlisted_assets_and_can_be_reused(self):
        (self.clone / "untrusted.py").write_text("changed unrelated code", encoding="utf-8")
        report = self.run_install()
        self.assertEqual((report["records"], report["images"]), (1, 3))
        provenance = json.loads((self.target / "SOURCE.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["revision"], self.commit)
        self.assertEqual(len(provenance["hashes"]), 6)
        self.assertFalse((self.target / "untrusted.py").exists())
        self.assertFalse((self.target / "data/private.json").exists())
        other = self.root / "reused"
        self.run_install(source=self.target, destination=other)
        self.assertEqual((other / hair.INDEX).read_bytes(), (self.target / hair.INDEX).read_bytes())
        before = (other / self.row["full"]).stat().st_mtime_ns
        (other / "keep.txt").write_text("user file", encoding="utf-8")
        self.run_install(source=self.target, destination=other)
        self.assertEqual((other / self.row["full"]).stat().st_mtime_ns, before)
        self.assertEqual((other / "keep.txt").read_text(encoding="utf-8"), "user file")

    def test_fixed_revision_zip_imports_only_allowlisted_files(self):
        archive = self.root / "upstream.zip"
        prefix = f"comfyui-hairstyle-gallery-{self.commit}/"
        with zipfile.ZipFile(archive, "w") as zipped:
            for path in self.clone.rglob("*"):
                if path.is_file() and ".git" not in path.relative_to(self.clone).parts:
                    zipped.write(path, prefix + path.relative_to(self.clone).as_posix())
            zipped.writestr(prefix + "../../escape", "never extracted")
        self.run_install(source=None, archive=archive)
        self.assertTrue((self.target / self.row["full"]).is_file())
        self.assertFalse((self.target / "untrusted.py").exists())
        self.assertFalse((self.root / "escape").exists())

    def test_wrong_revision_and_unrecorded_directory_rejected(self):
        with patch.object(hair, "COMMIT", "0" * 40), self.assertRaisesRegex(ValueError, "pinned revision"):
            self.run_install()
        unrecorded = self.root / "unrecorded"
        unrecorded.mkdir()
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.run_install(source=unrecorded)
        self.assertFalse(self.target.exists())

    def test_windows_crlf_metadata_matches_pinned_git_text(self):
        for path in (self.library / hair.INDEX, self.clone / "LICENSE", self.clone / "THIRD_PARTY_NOTICES.md"):
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.run_install(source=self.library)
        self.assertNotIn(b"\r\n", (self.target / hair.INDEX).read_bytes())

    def test_corrupt_original_hash_and_missing_image_never_publish(self):
        image = self.library / self.row["full"]
        output = BytesIO()
        Image.new("RGB", (2, 3), "blue").save(output, format="PNG")
        image.write_bytes(output.getvalue())
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            self.run_install()
        self.assertFalse(self.target.exists())
        image.unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.run_install()
        self.assertFalse(self.target.exists())

    def test_valid_but_changed_derivative_fails_pinned_tree(self):
        output = BytesIO()
        Image.new("RGB", (2, 3), "blue").save(output, format="WEBP")
        (self.library / self.row["thumb"]).write_bytes(output.getvalue())
        with self.assertRaisesRegex(ValueError, "Git tree mismatch"):
            self.run_install()
        self.assertFalse(self.target.exists())

    def test_path_duplicate_id_and_hashes_schema_rejected(self):
        for rows, expected in (([dict(self.row, full="../escape.png")], "asset path"),
                               ([self.row, self.row], "duplicate"),
                               ([dict(self.row, hashes={"full": "invalid"})], "hashes schema")):
            with self.subTest(expected=expected):
                self.write_rows(rows)
                with patch.object(hair, "EXPECTED_RECORDS", len(rows)), self.assertRaisesRegex(ValueError, expected):
                    self.run_install()
                self.assertFalse(self.target.exists())

    def test_installed_provenance_hashes_are_required_and_cannot_redefine_source(self):
        self.run_install()
        provenance_path = self.target / "SOURCE.json"
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        for changed in (dict(provenance, revision="HEAD"), dict(provenance, hashes={}),
                        dict(provenance, hashes={**provenance["hashes"], hair.INDEX: "0" * 64}),
                        dict(provenance, hashes={**provenance["hashes"], "extra.txt": "0" * 64})):
            provenance_path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.run_install(source=self.target, destination=self.root / "bad")
        self.assertFalse((self.root / "bad").exists())

    def test_user_library_destinations_are_protected(self):
        with patch.dict("os.environ", {"COMFYUI_HAIRSTYLE_GALLERY_USER_LIBRARY": str(self.target)}):
            with self.assertRaisesRegex(ValueError, "overlaps"):
                self.run_install()
        (self.target / "data").mkdir(parents=True)
        (self.target / "data/custom.json").write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "user-managed"):
            self.run_install()

    def test_publication_failure_preserves_old_index(self):
        (self.target / "data").mkdir(parents=True)
        index = self.target / hair.INDEX
        index.write_bytes(b"previous index")
        original = common.atomic_write
        def fail_asset(path, content):
            if path.is_relative_to(self.target):
                raise OSError("simulated publish error")
            return original(path, content)
        with patch.object(common, "atomic_write", side_effect=fail_asset), self.assertRaises(OSError):
            self.run_install()
        self.assertEqual(index.read_bytes(), b"previous index")

    def test_unified_cli_dispatches_all_and_supports_hairstyle_archive_target(self):
        with patch.object(pose, "run", return_value={}) as p, patch.object(costume, "run", return_value={}) as c, \
                patch.object(hair, "run", return_value={}) as h, redirect_stdout(StringIO()):
            with patch.object(sys, "argv", ["install_libraries.py", "--library", "all", "--destination", str(self.root),
                                           "--hairstyle-source", str(self.clone), "--hairstyle-destination", str(self.target)]):
                common.main()
            self.assertEqual(p.call_count, 1)
            self.assertEqual(c.call_count, 1)
            h.assert_called_once_with(source=self.clone, destination=self.target, archive=None)
            h.reset_mock()
            with patch.object(sys, "argv", ["install_libraries.py", "--library", "hairstyle", "--hairstyle-archive", "fixture.zip"]):
                common.main()
            h.assert_called_once_with(source=None, destination=None, archive=Path("fixture.zip"))
        self.assertEqual(common.MAX_ARCHIVE_BYTES, 1200 * 1024 * 1024)
        self.assertGreater(hair.MAX_ARCHIVE_BYTES, 2 * 1024 ** 3)


if __name__ == "__main__":
    unittest.main()
