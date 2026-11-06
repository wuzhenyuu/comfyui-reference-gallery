"""CLI import regressions with fresh Python processes and no library downloads."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = ("pose", "costume", "hairstyle")
SCRIPTS = ("install_libraries.py", *(f"install_{name}_library.py" for name in LIBRARIES))


class InstallerCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="reference-gallery-cli-")
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name).resolve()
        cls.scripts = cls.root / "插件 with spaces" / "scripts"
        cls.scripts.mkdir(parents=True)
        for name in SCRIPTS:
            shutil.copy2(ROOT / "scripts" / name, cls.scripts / name)
        cls.cwd = cls.root / "unrelated working directory"
        cls.cwd.mkdir()
        # A cwd/PYTHONPATH workaround must not import these unrelated modules.
        for name in SCRIPTS:
            (cls.cwd / name).write_text("raise RuntimeError('wrong installer directory')\n", encoding="utf-8")
        cls.missing_source = cls.root / "missing-offline-source"
        cls.destination = cls.root / "must-not-be-published"

    def run_cli(self, script, isolated, *arguments):
        environment = dict(os.environ, PYTHONPATH=str(self.cwd))
        flags = ["-I", "-S"] if isolated else []
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", *flags, str(self.scripts / script), *arguments],
            cwd=self.cwd, env=environment, capture_output=True,
            text=True, encoding="utf-8", timeout=20,
        )

    def assert_reached_offline_source(self, result):
        # The real runner rejects this absent source before any network or writes.
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FileNotFoundError", result.stderr)
        self.assertIn("missing-offline-source", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)
        self.assertNotIn("Downloading", result.stdout)
        self.assertFalse(self.destination.exists())

    def test_unified_cli_help_with_normal_and_isolated_python(self):
        for isolated in (False, True):
            with self.subTest(isolated=isolated):
                result = self.run_cli("install_libraries.py", isolated, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--library", result.stdout)

    def test_unified_cli_loads_each_library_without_implicit_script_path(self):
        for isolated in (False, True):
            for library in (*LIBRARIES, "all"):
                with self.subTest(isolated=isolated, library=library):
                    sources = ("--source", str(self.missing_source)) if library != "all" else tuple(
                        argument for name in LIBRARIES
                        for argument in (f"--{name}-source", str(self.missing_source))
                    )
                    result = self.run_cli(
                        "install_libraries.py", isolated, "--library", library, *sources,
                        "--destination", str(self.destination),
                    )
                    self.assert_reached_offline_source(result)

    def test_standalone_cli_help_without_implicit_script_path(self):
        for isolated in (False, True):
            for library in LIBRARIES:
                with self.subTest(isolated=isolated, library=library):
                    result = self.run_cli(f"install_{library}_library.py", isolated, "--help")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("--source", result.stdout)

    def test_standalone_cli_reaches_real_offline_runner(self):
        for isolated in (False, True):
            for library in LIBRARIES:
                with self.subTest(isolated=isolated, library=library):
                    result = self.run_cli(
                        f"install_{library}_library.py", isolated,
                        "--source", str(self.missing_source), "--destination", str(self.destination),
                    )
                    self.assert_reached_offline_source(result)


if __name__ == "__main__":
    unittest.main()
