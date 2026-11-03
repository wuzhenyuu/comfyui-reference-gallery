"""The merged root preserves old node IDs, routes and ComfyUI metadata."""
import importlib.util
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = Path(sys.executable).resolve().parents[2]
if (COMFY_ROOT / "comfy_api").is_dir():
    sys.path.insert(0, str(COMFY_ROOT))
if importlib.util.find_spec("comfy_api") is None:
    raise unittest.SkipTest("Run merged-package tests using the ComfyUI virtual environment")
from comfy_api.latest import io


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("reference_gallery_package_tests", ROOT / "__init__.py",
                                                     submodule_search_locations=[str(ROOT)])
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        server = types.ModuleType("server")
        cls.routes = web.RouteTableDef()
        server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=cls.routes))
        with patch.dict(sys.modules, {"server": server}):
            spec.loader.exec_module(cls.module)

    def test_all_four_existing_ids_and_outputs_survive_root_aggregation(self):
        nodes = self.module.NODE_CLASS_MAPPINGS
        self.assertEqual(set(nodes), {"PoseGallery", "RandomPoseGallery", "CostumeGallery", "RandomCostumeGallery"})
        self.assertEqual(set(nodes), set(self.module.NODE_DISPLAY_NAME_MAPPINGS))
        self.assertEqual(self.module.WEB_DIRECTORY, "./web")
        for name, node in nodes.items():
            self.assertEqual(tuple(node.RETURN_TYPES), ("IMAGE", "INT", "INT", "STRING", "STRING", "STRING"), name)
        self.assertEqual(nodes["PoseGallery"].RETURN_NAMES, ("image", "width", "height", "pose_id", "description", "action"))
        self.assertEqual(tuple(nodes["CostumeGallery"].RETURN_NAMES), ("image", "width", "height", "costume_id", "description", "keywords"))
        self.assertEqual(nodes["PoseGallery"].FUNCTION, "load_pose")
        self.assertEqual(nodes["RandomPoseGallery"].FUNCTION, "load_random")
        self.assertEqual(nodes["CostumeGallery"].FUNCTION, "EXECUTE_NORMALIZED")
        self.assertTrue(issubclass(nodes["CostumeGallery"], io.ComfyNode))
        self.assertEqual(nodes["CostumeGallery"].INPUT_TYPES()["required"]["costume_id"][1]["default"], "real:SPR-0001")
        self.assertTrue(nodes["RandomCostumeGallery"].HAS_INTERMEDIATE_OUTPUT)
        self.assertFalse(nodes["CostumeGallery"].HAS_INTERMEDIATE_OUTPUT)

    def test_unchanged_routes_register_once_and_share_web_root(self):
        routes = [(route.method, route.path) for route in self.routes]
        self.assertEqual(len(routes), len(set(routes)))
        for route in (("GET", "/pose_gallery/gallery"), ("GET", "/pose_gallery/catalog"),
                      ("POST", "/pose_gallery/upload"), ("POST", "/pose_gallery/manage/apply"),
                      ("GET", "/pose_gallery/ui/{filename}"), ("GET", "/costume_gallery/gallery"),
                      ("GET", "/costume_gallery/catalog"), ("GET", "/costume_gallery/assets/{kind}/{costume_id}")):
            self.assertIn(route, routes)
        self.assertEqual(self.module.pose.WEB_ROOT, ROOT / "web")
        self.assertEqual(self.module.costume.catalog.WEB_ROOT, ROOT / "web")

    def test_existing_user_directory_and_environment_overrides_remain_compatible(self):
        import folder_paths
        pose_catalog = self.module.pose._random_catalog
        expected = Path(os.environ.get("COMFYUI_POSE_GALLERY_USER_LIBRARY",
                                      Path(folder_paths.get_user_directory()) / "pose_gallery")).resolve()
        self.assertEqual(pose_catalog.USER_LIBRARY, expected)
        with tempfile.TemporaryDirectory() as directory:
            env = {"COMFYUI_POSE_GALLERY_LIBRARY": str(Path(directory) / "pose"),
                   "COMFYUI_POSE_GALLERY_USER_LIBRARY": str(Path(directory) / "existing-user"),
                   "COMFYUI_COSTUME_GALLERY_LIBRARY": str(Path(directory) / "costume")}
            with patch.dict(os.environ, env):
                for package, variable in (("pose", "COMFYUI_POSE_GALLERY_LIBRARY"),
                                          ("costume", "COMFYUI_COSTUME_GALLERY_LIBRARY")):
                    spec = importlib.util.spec_from_file_location("reference_env_" + package, ROOT / package / "catalog.py")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.assertEqual(module.LIBRARY, Path(env[variable]).resolve())
                    if package == "pose":
                        self.assertEqual(module.USER_LIBRARY, Path(env["COMFYUI_POSE_GALLERY_USER_LIBRARY"]).resolve())

    def test_original_http_urls_serve_the_shared_web_files(self):
        async def scenario():
            app = web.Application()
            app.add_routes(self.routes)
            async with TestClient(TestServer(app)) as client:
                for url, filename in (("/pose_gallery/gallery", "pose_gallery.html"),
                                      ("/costume_gallery/gallery", "costume_gallery.html"),
                                      ("/pose_gallery/ui/i18n.mjs", "i18n.mjs"),
                                      ("/pose_gallery/ui/custom_upload.mjs", "custom_upload.mjs"),
                                      ("/costume_gallery/ui/gallery.mjs", "gallery.mjs"),
                                      ("/costume_gallery/ui/gallery.css", "gallery.css")):
                    with self.subTest(url=url):
                        response = await client.get(url)
                        self.assertEqual(response.status, 200)
                        self.assertEqual(await response.read(), (ROOT / "web" / filename).read_bytes())
                for url in ("/pose_gallery/ui/__init__.py", "/costume_gallery/ui/catalog.py"):
                    response = await client.get(url)
                    self.assertEqual(response.status, 404)
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
