"""Validated local costume references. Catalog access never downloads assets."""
import hashlib
import json
import os
import random
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT.parent / "web"
LIBRARY = Path(os.environ.get("COMFYUI_COSTUME_GALLERY_LIBRARY", ROOT / "library")).resolve()
CATEGORIES = (
    ("spring", "春装", "Spring"), ("summer", "夏装", "Summer"),
    ("autumn", "秋装", "Autumn"), ("winter", "冬装", "Winter"),
    ("lingerie", "内衣", "Lingerie"), ("party", "派对", "Party"),
    ("swimwear", "泳装", "Swimwear"), ("sexy", "性感", "Sexy"),
)
CATEGORY_VALUES = tuple(row[0] for row in CATEGORIES)
IDENTITY = re.compile(r"(real|anime):([A-Za-z0-9_-]{1,80})\Z")


def contained_path(relative):
    root = LIBRARY.resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("服装素材路径越出图库目录 / Costume asset escapes the library")
    return target


@lru_cache(maxsize=4)
def _read_catalog(path, modified, size):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("服装索引不是有效 JSON / Invalid costume catalog JSON") from exc
    if (not isinstance(payload, dict) or payload.get("schema_version") != 1
            or not isinstance(payload.get("source"), dict) or not isinstance(payload.get("items"), list)
            or any(not isinstance(payload["source"].get(key), str) for key in ("url", "commit"))):
        raise ValueError("服装索引格式错误 / Invalid costume catalog schema")
    seen = set()
    for row in payload["items"]:
        if not isinstance(row, dict):
            raise ValueError("服装索引含无效条目 / Invalid costume record")
        identity = row.get("id")
        match = IDENTITY.fullmatch(identity) if isinstance(identity, str) else None
        if not match or identity in seen:
            raise ValueError("服装索引含无效或重复 ID / Invalid or duplicate costume ID")
        seen.add(identity)
        library, source_id = match.groups()
        if row.get("library") != library or row.get("source_id") != source_id or row.get("category") not in CATEGORY_VALUES:
            raise ValueError("服装编号或分类不匹配 / Costume identity or category mismatch")
        for key in ("category_zh", "category_en", "keywords_en", "keywords_zh"):
            if not isinstance(row.get(key), str):
                raise ValueError("服装索引缺少文本字段 / Missing costume text field")
        for field, directory in (("image", "img"), ("thumbnail", "thumbs")):
            if row.get(field) != f"{library}/{directory}/{source_id}.webp":
                raise ValueError("服装索引含无效图片路径 / Invalid costume image path")
    return payload


def read_catalog():
    path = contained_path("catalog.json")
    if not path.is_file():
        raise FileNotFoundError("服装索引缺失，请安装 library/catalog.json / Costume catalog is missing: library/catalog.json")
    stat = path.stat()
    return _read_catalog(str(path), stat.st_mtime_ns, stat.st_size)


def item(costume_id):
    if not isinstance(costume_id, str) or not IDENTITY.fullmatch(costume_id):
        raise ValueError("无效服装 ID / Invalid costume ID")
    row = next((row for row in read_catalog()["items"] if row["id"] == costume_id), None)
    if row is None:
        raise ValueError("未知服装 ID / Unknown costume ID: " + costume_id)
    return row


def asset(kind, costume_id):
    if kind not in ("img", "thumb"):
        raise ValueError("无效服装图片类型 / Invalid costume asset kind")
    row = item(costume_id)
    target = contained_path(row["image" if kind == "img" else "thumbnail"])
    if not target.is_file():
        raise FileNotFoundError("服装图片缺失 / Missing costume image: " + costume_id)
    return target


def candidates(library="all", category="all", query=""):
    if library not in ("all", "real", "anime") or category not in ("all", *CATEGORY_VALUES) or not isinstance(query, str):
        raise ValueError("无效服装筛选 / Invalid costume filter")
    payload = read_catalog()
    aliases = payload["source"].get("search_aliases", {})
    terms = [(term, aliases.get(term, term).casefold()) for term in query.casefold().split()]
    result = []
    for row in payload["items"]:
        if library != "all" and row["library"] != library:
            continue
        if category != "all" and row["category"] != category:
            continue
        text = " ".join(row[key] for key in ("id", "source_id", "category", "category_zh", "category_en", "keywords_en", "keywords_zh")).casefold()
        if any(original not in text and translated not in text for original, translated in terms):
            continue
        if contained_path(row["image"]).is_file():
            result.append(row)
    if not result:
        raise ValueError("当前筛选没有可用服装原图，请调整筛选或补齐素材 / No available costume originals match these filters")
    return sorted(result, key=lambda row: row["id"])


def select_random(library="all", category="all", query="", seed=0):
    if type(seed) is not int or not 0 <= seed <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("无效随机种子 / Invalid random seed")
    return random.Random(seed).choice(candidates(library, category, query))


def text_outputs(row, language):
    if language not in ("zh", "en"):
        raise ValueError("无效输出语言 / Invalid output language")
    keywords = row["keywords_" + language] or row["keywords_en"] or row["keywords_zh"]
    labels = {"real": ("写实服装", "Realistic costume"), "anime": ("动漫服装", "Anime costume")}
    label = labels[row["library"]][language == "en"]
    return " / ".join(value for value in (label, row["category_" + language], keywords) if value), keywords


def fingerprint(row, language):
    text_outputs(row, language)
    digest = hashlib.sha256(asset("img", row["id"]).read_bytes())
    digest.update(json.dumps([row, language], ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def browser_payload():
    payload = read_catalog()
    rows = []
    for row in payload["items"]:
        encoded = quote(row["id"], safe="")
        rows.append({**row, "image_url": f"/costume_gallery/assets/img/{encoded}",
                     "thumbnail_url": f"/costume_gallery/assets/thumb/{encoded}"})
    return {"items": rows, "counts": {"total": len(rows), "real": sum(row["library"] == "real" for row in rows),
                                      "anime": sum(row["library"] == "anime" for row in rows)},
            "categories": [{"value": value, "label_zh": zh, "label_en": en} for value, zh, en in CATEGORIES],
            "source": payload["source"]}
