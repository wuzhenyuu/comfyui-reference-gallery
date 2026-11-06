#!/usr/bin/env python3
"""Explicit pinned costume installation; --source and --archive work offline."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import tempfile

# Embedded Python may omit this directory from its isolated search path.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from install_libraries import (ROOT, DirectorySource, atomic_write, check_destination,
                               open_input, publish, safe_path)

COMMIT = "b236f0118e3a0195d1c71a7945f45294199f9607"
SOURCE_URL = "https://github.com/paipiange/nvzhuang"
DOWNLOAD_URLS = (f"https://codeload.github.com/paipiange/nvzhuang/zip/{COMMIT}",
                 f"https://github.com/paipiange/nvzhuang/archive/{COMMIT}.zip")
COUNTS = {"real": 1407, "anime": 1320}
DEFAULT_DESTINATION = Path(os.environ.get("COMFYUI_COSTUME_GALLERY_LIBRARY", ROOT / "costume/library"))
CATEGORIES = {
    "春": ("spring", "春", "Spring"), "夏": ("summer", "夏", "Summer"),
    "秋": ("autumn", "秋", "Autumn"), "冬": ("winter", "冬", "Winter"),
    "ランジェリー": ("lingerie", "内衣", "Lingerie"), "パーティ": ("party", "派对", "Party"),
    "水着": ("swimwear", "泳装", "Swimwear"), "セクシー": ("sexy", "性感", "Sexy"),
}


def parse_data(text: str, variable: str, expected_count: int) -> list[dict]:
    match = re.search(r"\bconst\s+" + re.escape(variable) + r"\s*=\s*(\[.*\])\s*;\s*$", text, re.DOTALL)
    if not match:
        raise ValueError(f"Cannot locate JSON array {variable}")
    records = json.loads(match.group(1))
    if len(records) != expected_count:
        raise ValueError(f"Unexpected {variable} count: {len(records)}")
    ids = set()
    required = {"id", "カテゴリ", "キーワード", "サムネ", "画像", "原寸"}
    for item in records:
        if not isinstance(item, dict) or set(item) != required or not all(isinstance(v, str) for v in item.values()):
            raise ValueError(f"Unexpected record schema in {variable}")
        if not re.fullmatch(r"[A-Z]{3}-[0-9]{4}", item["id"]) or item["id"] in ids:
            raise ValueError(f"Invalid or duplicate source ID: {item['id']}")
        ids.add(item["id"])
        if item["カテゴリ"] not in CATEGORIES:
            raise ValueError("Unknown category")
    return records


def parse_dictionary(text: str, variable: str, expected_count: int) -> dict[str, str]:
    """Parse only the upstream's flat, quoted string pairs; never evaluate JS."""
    match = re.search(r"\bconst\s+" + re.escape(variable) + r"\s*=\s*\{([^{}]*)\}\s*;", text)
    if not match:
        raise ValueError(f"Cannot locate dictionary {variable}")
    remaining = match.group(1)
    result = {}
    pair = re.compile(r"\s*'([^'\\]*)'\s*:\s*'([^'\\]*)'\s*(?:,|$)")
    while remaining.strip():
        found = pair.match(remaining)
        if not found or found.group(1) in result:
            raise ValueError(f"Unsupported dictionary syntax in {variable}")
        result[found.group(1)] = found.group(2)
        remaining = remaining[found.end():]
    if len(result) != expected_count:
        raise ValueError(f"Unexpected {variable} count: {len(result)}")
    return result


def webp_dimensions(content: bytes) -> tuple[int, int]:
    """Validate the WebP container header and obtain dimensions, without Pillow."""
    if len(content) < 30 or content[:4] != b"RIFF" or content[8:12] != b"WEBP":
        raise ValueError("Invalid WebP header")
    if struct.unpack_from("<I", content, 4)[0] + 8 != len(content):
        raise ValueError("WebP RIFF length does not match content")
    kind = content[12:16]
    if kind == b"VP8X":
        dimensions = (int.from_bytes(content[24:27], "little") + 1, int.from_bytes(content[27:30], "little") + 1)
    elif kind == b"VP8 ":
        if content[23:26] != b"\x9d\x01\x2a":
            raise ValueError("Invalid WebP VP8 frame header")
        dimensions = tuple(value & 16383 for value in struct.unpack_from("<HH", content, 26))
    elif kind == b"VP8L" and content[20] == 47:
        packed = int.from_bytes(content[21:25], "little")
        dimensions = ((packed & 16383) + 1, ((packed >> 14) & 16383) + 1)
    else:
        raise ValueError("Unsupported WebP frame header")
    if not all(0 < value <= 16384 for value in dimensions):
        raise ValueError("Invalid WebP dimensions")
    return dimensions


def read_license(reader, installed: bool) -> bytes:
    if installed:
        path = ROOT / "sources/costume/LICENSE.upstream.txt"
        content = path.read_bytes()
    else:
        content = reader.read("LICENSE", 16384)
    if not content.startswith(b"MIT License") or b"Copyright (c) 2026 paipiange" not in content:
        raise ValueError("Unexpected upstream costume license")
    return content


def prepare(reader):
    installed = isinstance(reader, DirectorySource) and reader.exists("catalog.json")
    if installed:
        catalog = json.loads(reader.read("catalog.json", 4 * 1024 * 1024))
        source = catalog.get("source", {})
        if catalog.get("schema_version") != 1 or source.get("commit") != COMMIT or source.get("url") != SOURCE_URL:
            raise ValueError("Installed costume source does not record the pinned revision")
        translations = source.get("keyword_translations", {})
        aliases = source.get("search_aliases", {})
        if len(translations) != 87 or len(aliases) != 79 or any(
                not isinstance(k, str) or not isinstance(v, str)
                for dictionary in (translations, aliases) for k, v in dictionary.items()):
            raise ValueError("Invalid recorded costume dictionaries")
        items = catalog.get("items", [])
    else:
        if isinstance(reader, DirectorySource):
            reader.verify_clone(COMMIT)
        frontend = reader.read("index.html", 2 * 1024 * 1024).decode("utf-8")
        translations = parse_dictionary(frontend, "EN2ZH", 87)
        aliases = parse_dictionary(frontend, "ZH_ALIAS", 79)
        items = []
        for library, filename, variable in (("real", "data.js", "D"), ("anime", "data-anime.js", "D_ANIME")):
            records = parse_data(reader.read(filename, 2 * 1024 * 1024).decode("utf-8"), variable, COUNTS[library])
            for row in records:
                identity = row["id"]
                category, category_zh, category_en = CATEGORIES[row["カテゴリ"]]
                for field, folder in (("画像", "img"), ("サムネ", "thumbs")):
                    expected = ("anime/" if library == "anime" else "") + f"{folder}/{identity}.webp"
                    if row[field] != expected:
                        raise ValueError("Unexpected source costume image path")
                items.append({"id": f"{library}:{identity}", "source_id": identity, "library": library,
                              "category": category, "category_zh": category_zh, "category_en": category_en,
                              "keywords_en": row["キーワード"],
                              "keywords_zh": " ".join(translations.get(word, word) for word in row["キーワード"].split()),
                              "image": f"{library}/img/{identity}.webp", "thumbnail": f"{library}/thumbs/{identity}.webp"})
    counts, identities, pending = Counter(), set(), []
    required = {"id", "source_id", "library", "category", "category_zh", "category_en",
                "keywords_en", "keywords_zh", "image", "thumbnail"}
    for item in items:
        if not isinstance(item, dict) or set(item) != required or not all(isinstance(v, str) for v in item.values()):
            raise ValueError("Invalid installed costume record schema")
        library, identity = item["library"], item["source_id"]
        if library not in COUNTS or not re.fullmatch(r"[A-Z]{3}-[0-9]{4}", identity):
            raise ValueError("Invalid costume library or source ID")
        if item["id"] != f"{library}:{identity}" or item["id"] in identities:
            raise ValueError("Duplicate or invalid namespaced costume ID")
        if (item["category"], item["category_zh"], item["category_en"]) not in CATEGORIES.values():
            raise ValueError("Invalid costume category")
        counts[library] += 1
        identities.add(item["id"])
        for field, folder in (("image", "img"), ("thumbnail", "thumbs")):
            expected = f"{library}/{folder}/{identity}.webp"
            if item[field] != expected:
                raise ValueError("Unsafe or unexpected costume asset path")
            source = expected if installed else "assets/" + ("anime/" if library == "anime" else "") + f"{folder}/{identity}.webp"
            pending.append((source, expected))
    if dict(counts) != COUNTS:
        raise ValueError(f"Unexpected costume record counts: {dict(counts)}")
    catalog = {"schema_version": 1,
               "source": {"url": SOURCE_URL, "commit": COMMIT, "search_aliases": aliases,
                          "keyword_translations": translations}, "items": items}
    return catalog, pending, read_license(reader, installed)


def run(source: Path | None = None, destination: Path | None = None, archive: Path | None = None) -> dict:
    if source is not None:
        source = Path(source).expanduser().resolve(strict=True)
        if (source / "library/catalog.json").is_file():
            source = source / "library"
    destination = check_destination(Path(destination) if destination else DEFAULT_DESTINATION,
                                    "COMFYUI_COSTUME_GALLERY_USER_LIBRARY")
    dimensions, total_bytes = {}, 0
    with open_input(source, archive, DOWNLOAD_URLS, f"nvzhuang-{COMMIT}/") as reader:
        catalog, pending, license_bytes = prepare(reader)
        # Validate and stage every owned image before publishing anything.
        with tempfile.TemporaryDirectory(prefix="reference-gallery-costume-stage-") as temporary:
            staged = Path(temporary)
            for source_name, target in pending:
                content = reader.read(source_name)
                width, height = webp_dimensions(content)
                dimensions.setdefault(str(PurePosixPath(target).parent), Counter())[f"{width}x{height}"] += 1
                total_bytes += len(content)
                atomic_write(safe_path(staged, target), content)
            atomic_write(staged / "LICENSE.upstream.txt", license_bytes)
            atomic_write(staged / "catalog.json", (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            publish(staged, destination, [target for _, target in pending] + ["LICENSE.upstream.txt", "catalog.json"], "catalog.json")
    return {"revision": COMMIT, "records": len(catalog["items"]), "images": len(pending),
            "image_bytes": total_bytes, "destination": str(destination),
            "dimensions": {key: dict(value) for key, value in dimensions.items()},
            "verification": "all references and WebP container/dimension headers; no full pixel decoding"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--source", type=Path, help="Existing pinned clone, plugin directory or installed library; no network")
    group.add_argument("--archive", type=Path, help="Existing pinned upstream ZIP; no network")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.source, arguments.destination, arguments.archive), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
