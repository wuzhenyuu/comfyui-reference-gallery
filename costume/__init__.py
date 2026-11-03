"""Local costume references for ComfyUI image editing workflows."""
import numpy as np
import torch
from aiohttp import web
from PIL import Image, ImageOps
from comfy_api.latest import ComfyExtension, io
from server import PromptServer

from . import catalog

def image_outputs(row, language):
    description, keywords = catalog.text_outputs(row, language)
    with Image.open(catalog.asset("img", row["id"])) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image = Image.alpha_composite(Image.new("RGBA", image.size, "white"), image).convert("RGB")
        width, height = image.size
        tensor = torch.from_numpy(np.asarray(image).astype(np.float32) / 255.0).unsqueeze(0)
    return tensor, width, height, row["id"], description, keywords


def outputs():
    return [io.Image.Output("image"), io.Int.Output("width"), io.Int.Output("height"),
            io.String.Output("costume_id"), io.String.Output("description"), io.String.Output("keywords")]


class CostumeGallery(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="CostumeGallery", display_name="Costume Gallery 服装图库", category="image/Costume Gallery",
                         description="浏览本地写实与动漫服装参考，输出原尺寸图像和服装关键词。",
                         inputs=[io.String.Input("costume_id", default="real:SPR-0001"),
                                 io.Combo.Input("language", options=["zh", "en"], default="zh")], outputs=outputs())

    @classmethod
    def validate_inputs(cls, costume_id, language="zh"):
        try:
            row = catalog.item(costume_id)
            catalog.asset("img", costume_id)
            catalog.text_outputs(row, language)
        except (ValueError, OSError) as exc:
            return str(exc)
        return True

    @classmethod
    def fingerprint_inputs(cls, costume_id, language="zh"):
        return catalog.fingerprint(catalog.item(costume_id), language)

    @classmethod
    def execute(cls, costume_id, language="zh") -> io.NodeOutput:
        return io.NodeOutput(*image_outputs(catalog.item(costume_id), language))


class RandomCostumeGallery(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="RandomCostumeGallery", display_name="Random Costume Gallery 随机服装图库",
                         category="image/Costume Gallery", description="按图库、分类和关键词筛选，以种子可重现地随机选择服装。",
                         has_intermediate_output=True,
                         inputs=[io.Combo.Input("library", options=["all", "real", "anime"], default="all"),
                                 io.Combo.Input("category", options=["all", *catalog.CATEGORY_VALUES], default="all"),
                                 io.String.Input("query", default=""),
                                 io.Int.Input("seed", default=0, min=0, max=0xFFFFFFFFFFFFFFFF, control_after_generate=True),
                                 io.Combo.Input("language", options=["zh", "en"], default="zh")], outputs=outputs())

    @classmethod
    def validate_inputs(cls, library="all", category="all", query="", seed=0, language="zh"):
        try:
            row = catalog.select_random(library, category, query, seed)
            catalog.text_outputs(row, language)
        except (ValueError, OSError) as exc:
            return str(exc)
        return True

    @classmethod
    def fingerprint_inputs(cls, library="all", category="all", query="", seed=0, language="zh"):
        return catalog.fingerprint(catalog.select_random(library, category, query, seed), language)

    @classmethod
    def execute(cls, library="all", category="all", query="", seed=0, language="zh") -> io.NodeOutput:
        row = catalog.select_random(library, category, query, seed)
        return io.NodeOutput(*image_outputs(row, language), ui={"costume_id": [row["id"]]})


class CostumeGalleryExtension(ComfyExtension):
    async def get_node_list(self):
        return [CostumeGallery, RandomCostumeGallery]


async def comfy_entrypoint():
    return CostumeGalleryExtension()


routes = PromptServer.instance.routes


@routes.get("/costume_gallery/catalog")
@routes.get("/costume_gallery/meta")
async def catalog_route(request):
    try:
        return web.json_response(catalog.browser_payload(), headers={"Cache-Control": "no-store"})
    except (ValueError, OSError) as exc:
        return web.json_response({"error": str(exc)}, status=503, headers={"Cache-Control": "no-store"})


@routes.get("/costume_gallery/assets/{kind}/{costume_id}")
async def asset_route(request):
    try:
        path = catalog.asset(request.match_info["kind"], request.match_info["costume_id"])
    except (ValueError, OSError):
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Cache-Control": "private, no-cache"})


@routes.get("/costume_gallery/gallery")
async def gallery_route(request):
    return web.FileResponse(catalog.WEB_ROOT / "costume_gallery.html", headers={"Cache-Control": "no-cache"})


@routes.get("/costume_gallery/ui/{filename}")
async def ui_route(request):
    filename = request.match_info["filename"]
    if filename not in ("gallery.mjs", "gallery.css"):
        raise web.HTTPNotFound()
    return web.FileResponse(catalog.WEB_ROOT / filename, headers={"Cache-Control": "no-cache"})
