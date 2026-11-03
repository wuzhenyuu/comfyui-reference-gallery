"""CPU-only node and HTTP checks against isolated temporary libraries."""
import asyncio
import importlib.util
import json
from pathlib import Path
import random
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
import torch
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
COMFY_ROOT = Path(sys.executable).resolve().parents[2]
if (COMFY_ROOT / 'comfy_api').is_dir():
    sys.path.insert(0, str(COMFY_ROOT))
if importlib.util.find_spec('comfy_api') is None:
    raise unittest.SkipTest("Run V3 backend tests using the ComfyUI virtual environment")
from comfy_api.latest import io
spec = importlib.util.spec_from_file_location("costume_gallery_tests", ROOT / "__init__.py",
                                              submodule_search_locations=[str(ROOT)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
server = types.ModuleType("server")
server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=web.RouteTableDef()))
with patch.dict(sys.modules, {"server": server}):
    spec.loader.exec_module(plugin)
catalog = plugin.catalog


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.patcher = patch.object(catalog, "LIBRARY", self.root)
        self.patcher.start()
        self.rows = [self.row("real", "SPR-0001", "spring", "black dress"),
                     self.row("anime", "SPR-0001", "spring", "white dress"),
                     self.row("real", "SUM-0001", "summer", "black shirt")]
        for row in self.rows:
            for field in ("image", "thumbnail"):
                path = self.root / row[field]
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (2, 3), (255, 0, 0, 128)).save(path, lossless=True)
        self.payload = {"schema_version": 1, "source": {"url": "https://example.test/source", "commit": "test",
                        "search_aliases": {"裙子": "dress", "黑色": "black"}}, "items": self.rows}
        self.write_index()

    def tearDown(self):
        catalog._read_catalog.cache_clear()
        self.patcher.stop()
        self.temporary.cleanup()

    def row(self, library, source_id, category, keywords):
        return {"id": f"{library}:{source_id}", "source_id": source_id, "library": library, "category": category,
                "category_zh": "春装" if category == "spring" else "夏装", "category_en": category.title(),
                "keywords_en": keywords, "keywords_zh": "",
                "image": f"{library}/img/{source_id}.webp", "thumbnail": f"{library}/thumbs/{source_id}.webp"}

    def write_index(self):
        (self.root / "catalog.json").write_text(json.dumps(self.payload, ensure_ascii=False), encoding="utf-8")
        catalog._read_catalog.cache_clear()

    def test_namespace_preserves_same_source_id_in_both_libraries(self):
        self.assertEqual(len(catalog.read_catalog()["items"]), 3)
        self.assertNotEqual(catalog.asset("img", "real:SPR-0001"), catalog.asset("img", "anime:SPR-0001"))
        self.payload["items"].append(dict(self.rows[0]))
        self.write_index()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            catalog.read_catalog()

    def test_rejects_unregistered_ids_paths_and_invalid_filters(self):
        for identity in ("SPR-0001", "../catalog.json", "real:SPR-0001/../../secret", "real:UNKNOWN"):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                catalog.asset("img", identity)
        with self.assertRaises(ValueError):
            catalog.asset("unknown", self.rows[0]["id"])
        with self.assertRaises(ValueError):
            catalog.candidates(library="../real")
        with self.assertRaises(ValueError):
            catalog.candidates(category="bad")
        with self.assertRaises(ValueError):
            catalog.select_random(seed=-1)
        self.rows[0]["image"] = "../outside.webp"
        self.write_index()
        with self.assertRaisesRegex(ValueError, "path"):
            catalog.read_catalog()

    def test_resolved_asset_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "outside.webp"
            Image.new("RGB", (1, 1)).save(target)
            path = self.root / self.rows[0]["image"]
            path.unlink()
            try:
                path.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"Symlink unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "escapes"):
                catalog.asset("img", self.rows[0]["id"])

    def test_filters_aliases_and_missing_originals(self):
        self.assertEqual([row["id"] for row in catalog.candidates("real", "spring", "黑色 裙子")], ["real:SPR-0001"])
        self.assertEqual(len(catalog.candidates(query="DRESS")), 2)
        (self.root / self.rows[1]["image"]).unlink()
        self.assertEqual(len(catalog.candidates(query="dress")), 1)
        with self.assertRaisesRegex(ValueError, "No available"):
            catalog.candidates(library="anime")
        self.assertIsInstance(plugin.RandomCostumeGallery.validate_inputs(query="no-match"), str)

    def test_seed_is_reproducible_independent_of_index_order(self):
        identities = sorted(row["id"] for row in self.rows)
        for seed in (0, 1, 9, 123, 0xFFFFFFFFFFFFFFFF):
            self.assertEqual(catalog.select_random(seed=seed)["id"], random.Random(seed).choice(identities))
        selected = catalog.select_random(seed=9)["id"]
        self.payload["items"] = list(reversed(self.rows))
        self.write_index()
        self.assertEqual(catalog.select_random(seed=9)["id"], selected)
        self.assertGreater(len({catalog.select_random(seed=seed)["id"] for seed in range(20)}), 1)

    def test_real_v3_schemas_and_missing_index_import_behavior(self):
        (self.root / "catalog.json").unlink()
        nodes = asyncio.run(asyncio.run(plugin.comfy_entrypoint()).get_node_list())
        self.assertEqual(nodes, [plugin.CostumeGallery, plugin.RandomCostumeGallery])
        schema = nodes[0].define_schema()
        self.assertIsInstance(schema, io.Schema)
        self.assertEqual(schema.node_id, "CostumeGallery")
        self.assertEqual([output.id for output in schema.outputs],
                         ["image", "width", "height", "costume_id", "description", "keywords"])
        random_schema = nodes[1].define_schema()
        self.assertTrue(random_schema.has_intermediate_output)
        self.assertTrue(nodes[1].HAS_INTERMEDIATE_OUTPUT)
        self.assertTrue(next(value for value in random_schema.inputs if value.id == "seed").control_after_generate)
        self.assertIn("missing", nodes[0].validate_inputs("real:SPR-0001"))

    def test_tensor_original_size_transparency_and_text_language(self):
        result = plugin.CostumeGallery.execute("real:SPR-0001", "en").result
        tensor, width, height, identity, description, keywords = result
        self.assertEqual(tensor.shape, (1, 3, 2, 3))
        self.assertEqual(tensor.dtype, torch.float32)
        self.assertEqual((width, height, identity), (2, 3, "real:SPR-0001"))
        np.testing.assert_allclose(tensor[0, 0, 0].numpy(), [1, 127 / 255, 127 / 255], atol=1e-6)
        self.assertEqual(keywords, "black dress")
        self.assertIn("Realistic costume / Spring", description)
        self.assertIn("写实服装 / 春装", plugin.CostumeGallery.execute(identity, "zh").result[4])
        random_result = plugin.RandomCostumeGallery.execute(seed=5)
        self.assertEqual(random_result.ui["costume_id"], [random_result.result[3]])

    def test_exif_orientation_and_fingerprint_changes(self):
        identity = self.rows[0]["id"]
        before = plugin.CostumeGallery.fingerprint_inputs(identity, "zh")
        self.assertNotEqual(before, plugin.CostumeGallery.fingerprint_inputs(identity, "en"))
        image = Image.new("RGB", (2, 3), "green")
        exif = image.getexif()
        exif[274] = 6
        image.save(catalog.asset("img", identity), lossless=True, exif=exif)
        result = plugin.CostumeGallery.execute(identity).result
        self.assertEqual(result[:1][0].shape, (1, 2, 3, 3))
        self.assertEqual(result[1:3], (3, 2))
        self.assertNotEqual(before, plugin.CostumeGallery.fingerprint_inputs(identity, "zh"))

    def test_random_ui_replay_marker_preserves_cache_fingerprint(self):
        # ComfyUI uses the V3 class marker to resend cached UI to new clients.
        node = plugin.RandomCostumeGallery
        self.assertTrue(node.HAS_INTERMEDIATE_OUTPUT)
        fingerprint = node.fingerprint_inputs(seed=42)
        self.assertEqual(fingerprint, node.fingerprint_inputs(seed=42))
        self.assertEqual(node.execute(seed=42).ui, node.execute(seed=42).ui)

    def test_http_catalog_assets_and_route_boundaries(self):
        async def scenario():
            app = web.Application()
            app.add_routes(plugin.routes)
            async with TestClient(TestServer(app)) as client:
                response = await client.get("/costume_gallery/catalog")
                self.assertEqual(response.status, 200)
                payload = await response.json()
                self.assertEqual(payload["counts"], {"total": 3, "real": 2, "anime": 1})
                self.assertEqual(len(payload["categories"]), 8)
                response = await client.get(payload["items"][0]["image_url"])
                self.assertEqual(response.status, 200)
                self.assertEqual(await response.read(), catalog.asset("img", self.rows[0]["id"]).read_bytes())
                for url in ("/costume_gallery/assets/img/real:UNKNOWN", "/costume_gallery/assets/bad/real:SPR-0001",
                            "/costume_gallery/assets/img/real%3A..%2Fcatalog.json", "/costume_gallery/ui/catalog.py"):
                    response = await client.get(url)
                    self.assertEqual(response.status, 404, url)
                response = await client.post("/costume_gallery/catalog")
                self.assertEqual(response.status, 405)
                (self.root / "catalog.json").unlink()
                response = await client.get("/costume_gallery/meta")
                self.assertEqual(response.status, 503)
                self.assertIn("missing", (await response.json())["error"])
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
