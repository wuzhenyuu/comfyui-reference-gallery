"""Allow-listed built-in and persistent user hairstyle assets."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARY = Path(os.environ.get("COMFYUI_HAIRSTYLE_GALLERY_LIBRARY", ROOT / "library")).resolve()
try:
    import folder_paths
    _USER_DIRECTORY = Path(folder_paths.get_user_directory())
except ImportError:
    _USER_DIRECTORY = Path.home() / ".comfyui" / "user"
USER_LIBRARY = Path(os.environ.get("COMFYUI_HAIRSTYLE_GALLERY_USER_LIBRARY", _USER_DIRECTORY / "hairstyle_gallery")).resolve()
FIELDS = {"full": ("full", ".png"), "thumb": ("thumb", ".webp"), "preview": ("preview", ".webp")}
NAME_EN = json.loads((ROOT / "translations/names.en.json").read_text(encoding="utf-8"))
HAIR_EN = {"ショート": "Short", "ミディアム": "Medium", "セミロング": "Medium-long", "ロング": "Long", "unknown": "Unspecified"}
HAIR_ZH = {"ショート": "短发", "ミディアム": "中发", "セミロング": "中长发", "ロング": "长发", "unknown": "未分类"}
ID_PATTERN = re.compile(r"[a-z0-9_-]{1,80}")


def localized(row, origin="builtin"):
    if origin == "user":
        name = row.get("name_en") or row["name_zh"]
        row = dict(row, section_zh="自定义发型", source_id="", style_zh=row["name_zh"])
        section = "Custom hairstyle"
        style = name
    else:
        name = NAME_EN.get(row["name_zh"], HAIR_EN.get(row.get("hair"), "Unknown") + " hairstyle")
        style = name if row.get("style") else ""
        section = "Mannequin hairstyle"
    searchable = [row.get("search", ""), row["id"], row.get("source_id", ""), row["name_zh"],
                  row.get("name_ja", ""), row.get("original_filename", ""), row.get("hair_zh", ""), name, HAIR_EN.get(row.get("hair"), "")]
    return dict(row, origin=origin, name_en=name, style_en=style, hair_en=HAIR_EN.get(row.get("hair"), "Unknown"),
                section_en=section, search=" ".join(searchable).lower())


@lru_cache(maxsize=4)
def _read_library(path, modified, size, origin="builtin"):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("发型索引格式错误")
    seen = set()
    for row in rows:
        identity = row.get("id") if isinstance(row, dict) else None
        if not isinstance(identity, str) or not ID_PATTERN.fullmatch(identity) or identity in seen:
            raise ValueError("发型索引包含无效或重复ID")
        seen.add(identity)
        if origin == "user" and not re.fullmatch(r"u-[a-f0-9]{32}", identity):
            raise ValueError("自定义发型编号无效")
        if origin == "builtin" and identity.startswith("u-"):
            raise ValueError("内置索引不能使用自定义编号")
        if row.get("section") != "hairstyle":
            raise ValueError("未知发型参考类型")
        if not isinstance(row.get("name_zh"), str) or not row["name_zh"]:
            raise ValueError("发型名称缺失")
        for kind, (field, suffix) in FIELDS.items():
            if row.get(field) != f"img/{kind}/{identity}{suffix}":
                raise ValueError("发型索引包含无效图片路径")
    return [localized(row, origin) for row in rows]


def _rows(root, relative, origin):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("发型索引路径无效")
    if not path.is_file():
        return []
    stat = path.stat()
    return _read_library(str(path), stat.st_mtime_ns, stat.st_size, origin)


def management_rules():
    """Read desired states only. Reading a catalog never changes library files."""
    path = (USER_LIBRARY / "data/builtin_changes.json").resolve()
    if not path.is_relative_to(USER_LIBRARY):
        raise ValueError("素材管理记录路径越界")
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1 or not isinstance(payload.get("rules"), dict):
        raise ValueError("素材管理记录格式错误")
    rules = payload["rules"]
    for identity, rule in rules.items():
        if (not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity) or identity.startswith("u-")
                or not isinstance(rule, dict) or rule.get("mode") not in ("thumb_only", "removed", "replace")):
            raise ValueError("素材管理记录无效")
        if rule["mode"] == "replace":
            if (not isinstance(rule.get("revision"), str) or not re.fullmatch(r"[a-f0-9]{32}", rule["revision"])
                    or any(type(rule.get(key)) is not int or rule[key] < 1 for key in ("w", "h"))
                    or rule["w"] * rule["h"] > 32_000_000
                    or not isinstance(rule.get("hashes"), dict)
                    or set(rule["hashes"]) != set(ASSET_FIELDS)
                    or any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in rule["hashes"].values())):
                raise ValueError("替换素材记录无效")
    return rules


def records(include_removed=False, availability=False):
    result = []
    rules = management_rules()
    for entry in _rows(LIBRARY, "data/hairstyle-zh.json", "builtin") + _rows(USER_LIBRARY, "data/custom.json", "user"):
        row = dict(entry)
        if row["origin"] == "builtin":
            rule = rules.get(row["id"], {})
            row["management_state"] = rule.get("mode", "default")
            if rule.get("mode") == "removed" and not include_removed:
                continue
            if rule.get("mode") == "replace":
                row.update(w=rule["w"], h=rule["h"], asset_version=rule["revision"], bytes=rule.get("bytes", row.get("bytes", 0)))
            if availability:
                target = (LIBRARY / row[ASSET_FIELDS[FULL_KIND]]).resolve()
                row["original_available"] = rule.get("mode") not in ("removed", "thumb_only") and target.is_relative_to(LIBRARY) and target.is_file()
        result.append(row)
    return result


def hairstyle(identity, include_removed=False):
    if not isinstance(identity, str) or not ID_PATTERN.fullmatch(identity):
        raise ValueError("无效发型ID")
    row = next((r for r in records(include_removed=include_removed) if r["id"] == identity), None)
    if row is None:
        if management_rules().get(identity, {}).get("mode") == "removed":
            raise ValueError("素材已删除。请先补回内置素材，再在“管理内置素材”中选择保留。Asset deleted; restore built-in files and choose to keep them in Manage built-in assets.")
        raise ValueError("未知发型ID：" + identity)
    return row


def asset(kind, filename):
    if kind not in FIELDS or Path(filename).name != filename or "\\" in filename:
        raise ValueError("无效发型图片路径")
    row = hairstyle(Path(filename).stem, include_removed=kind != FULL_KIND)
    if kind == FULL_KIND and row.get("management_state") == "thumb_only":
        raise FileNotFoundError("素材已删除，请先补回内置素材。Asset deleted; restore built-in files first.")
    field, suffix = FIELDS[kind]
    root = USER_LIBRARY if row["origin"] == "user" else LIBRARY
    relative = Path("img") / kind / filename
    target = (root / relative).resolve()
    if Path(filename).suffix != suffix or row[field] != relative.as_posix() or not target.is_relative_to(root):
        raise ValueError("图片不在发型图库允许范围内")
    if not target.is_file():
        raise FileNotFoundError("发型原图缺失：library/" + str(relative) + "，请检查完整素材库。")
    return target


def browser_payload():
    rows = [dict(r, **{field: f"assets/{kind}/{r['id']}{suffix}" + ("?v=" + r["asset_version"] if r.get("asset_version") else "") for kind, (field, suffix) in FIELDS.items()}) for r in records(availability=True)]
    builtin = sum(row["origin"] == "builtin" for row in rows)
    ranking = {"cats": list(HAIR_ZH), "labels": HAIR_ZH,
               "top": {h: [row["id"] for row in rows if row["hair"] == h][:10] for h in HAIR_ZH}}
    return {"records": rows, "meta": {"total": len(rows), "builtin_count": builtin, "user_count": len(rows) - builtin,
            "builtin_missing": not (LIBRARY / "data/hairstyle-zh.json").is_file(), "target": 893,
            "sections": {"hairstyle": len(rows)}}, "ranking": ranking}

GALLERY = "hairstyle"
FULL_KIND = "full"
ASSET_FIELDS = {kind: field for kind, (field, suffix) in FIELDS.items()}
PREFIXES = {kind: "img/" + kind for kind in FIELDS}
OPTIONAL_ASSETS = ()
INDEX_FILE = "data/hairstyle-zh.json"
