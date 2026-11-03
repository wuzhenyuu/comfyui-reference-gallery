#!/usr/bin/env python3
"""Explicit pinned pose installation; existing clones/libraries work offline."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import tempfile

from install_libraries import (ROOT, DirectorySource, atomic_write, check_destination,
                               open_input, publish, safe_path, validate_jpeg, validate_png)

COMMIT = "072a3690af6e7e0011abbe0fa1ccc08939fbb47d"
SOURCE_URL = "https://github.com/wangweihong/ai-pose-gallery-zh.git"
DOWNLOAD_URLS = (f"https://codeload.github.com/wangweihong/ai-pose-gallery-zh/zip/{COMMIT}",
                 f"https://github.com/wangweihong/ai-pose-gallery-zh/archive/{COMMIT}.zip")
EXPECTED_RECORDS = 1439
DEFAULT_DESTINATION = Path(os.environ.get("COMFYUI_POSE_GALLERY_LIBRARY", ROOT / "pose/library"))


def prepare(reader):
    if isinstance(reader, DirectorySource):
        if reader.exists("SOURCE.json"):
            provenance = json.loads(reader.read("SOURCE.json", 16384))
            if (provenance.get("revision") != COMMIT or provenance.get("url", "").removesuffix(".git") != SOURCE_URL.removesuffix(".git")
                    or provenance.get("images") != EXPECTED_RECORDS):
                raise ValueError("Installed pose source does not record the pinned revision and count")
        else:
            reader.verify_clone(COMMIT)
    records_bytes = reader.read("data/pose-zh.json", 4 * 1024 * 1024)
    meta_bytes = reader.read("data/meta-zh.json", 1024 * 1024)
    records, metadata = json.loads(records_bytes), json.loads(meta_bytes)
    if not isinstance(records, list) or len(records) != EXPECTED_RECORDS:
        raise ValueError("Unexpected pose record count")
    groups = metadata.get("体系分类") if isinstance(metadata, dict) else None
    if not isinstance(groups, list) or not groups or len(set(groups)) != len(groups) or not all(isinstance(v, str) for v in groups):
        raise ValueError("Invalid pose category metadata")
    pending, ids = [], set()
    for row in records:
        required = {"id", "体系", "姿势编号", "分类", "姿势名称", "角度", "缩略图", "原图", "检索"}
        if not isinstance(row, dict) or not required.issubset(row) or not all(isinstance(row[k], str) for k in required):
            raise ValueError("Invalid pose record schema")
        identity = row["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identity) or identity in ids:
            raise ValueError("Unsafe or duplicate pose ID")
        if row["体系"] not in groups:
            raise ValueError("Pose record references an unknown category group")
        ids.add(identity)
        for field, folder, extension in (("原图", "img", "png"), ("缩略图", "thumbs", "jpg")):
            expected = f"{folder}/{identity}.{extension}"
            if row[field] != expected:
                raise ValueError("Unsafe or unexpected pose image path")
            pending.append(expected)
    license_bytes = reader.read("LICENSE", 16384)
    if not license_bytes.startswith(b"MIT License") or b"Copyright (c) 2026 Anhao" not in license_bytes:
        raise ValueError("Unexpected upstream pose license")
    readme = reader.read("README.md", 1024 * 1024)
    return records, pending, records_bytes, meta_bytes, license_bytes, readme


def run(source: Path | None = None, destination: Path | None = None, archive: Path | None = None) -> dict:
    if source is not None:
        source = Path(source).expanduser().resolve(strict=True)
        if (source / "library/SOURCE.json").is_file():
            source = source / "library"
    destination = check_destination(Path(destination) if destination else DEFAULT_DESTINATION,
                                    "COMFYUI_POSE_GALLERY_USER_LIBRARY")
    total_bytes, dimensions = 0, {}
    with open_input(source, archive, DOWNLOAD_URLS, f"ai-pose-gallery-zh-{COMMIT}/") as reader:
        records, pending, rows, meta, license_bytes, readme = prepare(reader)
        with tempfile.TemporaryDirectory(prefix="reference-gallery-pose-stage-") as temporary:
            staged = Path(temporary)
            for relative in pending:
                content = reader.read(relative)
                width, height = validate_png(content) if relative.endswith(".png") else validate_jpeg(content)
                folder = relative.split("/", 1)[0]
                dimensions.setdefault(folder, Counter())[f"{width}x{height}"] += 1
                total_bytes += len(content)
                atomic_write(safe_path(staged, relative), content)
            provenance = {"url": SOURCE_URL, "revision": COMMIT, "images": len(records)}
            for relative, content in (("data/meta-zh.json", meta), ("LICENSE", license_bytes), ("README.md", readme),
                                      ("SOURCE.json", (json.dumps(provenance, indent=2) + "\n").encode()),
                                      ("data/pose-zh.json", rows)):
                atomic_write(safe_path(staged, relative), content)
            publish(staged, destination,
                    pending + ["data/meta-zh.json", "LICENSE", "README.md", "SOURCE.json", "data/pose-zh.json"],
                    "data/pose-zh.json")
    return {"revision": COMMIT, "records": len(records), "images": len(pending), "image_bytes": total_bytes,
            "destination": str(destination), "dimensions": {k: dict(v) for k, v in dimensions.items()},
            "verification": "all referenced files, PNG chunk CRCs, PNG/JPEG dimensions; no full pixel decoding"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--source", type=Path, help="Existing clean pinned clone, plugin directory or recorded installed library; no network")
    group.add_argument("--archive", type=Path, help="Existing pinned upstream ZIP; no network")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.source, arguments.destination, arguments.archive), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
