#!/usr/bin/env python3
"""Explicit pinned hairstyle installation; never executes upstream code or models."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

# Embedded Python may omit this directory from its isolated search path.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from install_libraries import (ROOT, DirectorySource, atomic_write, check_destination,
                               open_input, publish, safe_path, validate_png)
from install_costume_library import webp_dimensions

COMMIT = "f72dc1881f92a40e52bd0fbf53d33c24d35c4c5b"
SOURCE_URL = "https://github.com/wangweihong/comfyui-hairstyle-gallery"
DOWNLOAD_URLS = (f"https://codeload.github.com/wangweihong/comfyui-hairstyle-gallery/zip/{COMMIT}",
                 f"https://github.com/wangweihong/comfyui-hairstyle-gallery/archive/{COMMIT}.zip")
EXPECTED_RECORDS = 893
MAX_ARCHIVE_BYTES = 2560 * 1024 * 1024
INDEX = "data/hairstyle-zh.json"
DEFAULT_DESTINATION = Path(os.environ.get("COMFYUI_HAIRSTYLE_GALLERY_LIBRARY", ROOT / "hairstyle/library"))
KINDS = {"full": ".png", "preview": ".webp", "thumb": ".webp"}
# These three Git trees pin all image bytes, without bundling source metadata or
# a 2,679-entry asset manifest. The index and notices are pinned separately.
IMAGE_TREES = {"full": "3ddee00de548daea84de458210a3d5dfcf4154ea",
               "preview": "2f897cd491e6dd24f19e20f57404e64983f1a40f",
               "thumb": "f81a4fe8419ddc941d4ac13dcb148ae46867bf5f"}
INDEX_SHA256 = "01ea2a18bc33c0a41fcb64e25628a77da5b1c0bd455407b44476c821227b3556"
NOTICE_HASHES = {
    "LICENSE.upstream.txt": "e7a3a8d04143f6d5278dc80952f33f9958fff586a77369b04d8a1acd14af3e04",
    "THIRD_PARTY_NOTICES.md": "e0480624d6a6c003a2b701b6cf09202246c564774a6d24202e8b634e7ec6a44d"}


def git_object(kind: str, content: bytes) -> str:
    return hashlib.sha1(f"{kind} {len(content)}\0".encode() + content).hexdigest()


def image_tree(blobs: dict[str, str]) -> str:
    body = b"".join(b"100644 " + name.encode("ascii") + b"\0" + bytes.fromhex(blob)
                    for name, blob in sorted(blobs.items()))
    return git_object("tree", body)


def check_hash(content: bytes, expected: str, label: str) -> str:
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA256 mismatch: {label}")
    return actual


def validate_records(content: bytes) -> list[dict]:
    rows = json.loads(content)
    if not isinstance(rows, list) or len(rows) != EXPECTED_RECORDS:
        raise ValueError("Unexpected hairstyle record count")
    ids = set()
    for row in rows:
        identity = row.get("id") if isinstance(row, dict) else None
        if not isinstance(identity, str) or not re.fullmatch(r"h-[a-z0-9_-]{1,70}", identity) or identity in ids:
            raise ValueError("Invalid or duplicate hairstyle ID")
        ids.add(identity)
        if row.get("section") != "hairstyle" or not isinstance(row.get("name_zh"), str) or not row["name_zh"]:
            raise ValueError("Invalid hairstyle record schema")
        if any(type(row.get(key)) is not int or not 0 < row[key] <= 16384 for key in ("w", "h")):
            raise ValueError("Invalid hairstyle dimensions")
        if not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", row["sha256"]):
            raise ValueError("Invalid original hairstyle SHA256")
        if "hashes" in row and (not isinstance(row["hashes"], dict) or set(row["hashes"]) != set(KINDS)
                or any(not isinstance(v, str) or not re.fullmatch(r"[a-f0-9]{64}", v) for v in row["hashes"].values())):
            raise ValueError("Invalid hairstyle hashes schema")
        for kind, suffix in KINDS.items():
            if row.get(kind) != f"img/{kind}/{identity}{suffix}":
                raise ValueError("Unsafe or unexpected hairstyle asset path")
    return rows


def installed_hashes(reader: DirectorySource) -> dict[str, str]:
    source = json.loads(reader.read("SOURCE.json", 1024 * 1024))
    hashes = source.get("hashes") if isinstance(source, dict) else None
    if (not isinstance(source, dict) or source.get("url") != SOURCE_URL or source.get("revision") != COMMIT
            or source.get("records") != EXPECTED_RECORDS or source.get("assets") != EXPECTED_RECORDS * 3
            or not isinstance(hashes, dict) or not hashes
            or any(not isinstance(k, str) or not isinstance(v, str) or not re.fullmatch(r"[a-f0-9]{64}", v)
                   for k, v in hashes.items())):
        raise ValueError("Installed hairstyle source must record the pinned revision and complete hashes")
    return hashes


def run(source: Path | None = None, destination: Path | None = None, archive: Path | None = None) -> dict:
    if source is not None and archive is not None:
        raise ValueError("Choose either a hairstyle source directory or archive")
    if source is not None:
        source = Path(source).expanduser().resolve(strict=True)
        if source.name == "library" and (source.parent / ".git").exists():
            source = source.parent
        elif not (source / ".git").exists() and (source / "library/SOURCE.json").is_file():
            source = source / "library"
    destination = check_destination(Path(destination) if destination else DEFAULT_DESTINATION,
                                    "COMFYUI_HAIRSTYLE_GALLERY_USER_LIBRARY")
    hashes, dimensions, trees, total_bytes = {}, {}, {kind: {} for kind in KINDS}, 0
    with open_input(source, archive, DOWNLOAD_URLS, f"comfyui-hairstyle-gallery-{COMMIT}/",
                    max_archive_bytes=MAX_ARCHIVE_BYTES) as reader:
        installed = isinstance(reader, DirectorySource) and not (reader.root / ".git").exists()
        expected_hashes = installed_hashes(reader) if installed else None
        if isinstance(reader, DirectorySource) and not installed:
            revision = subprocess.check_output(["git", "-C", str(reader.root), "rev-parse", "HEAD"], text=True).strip()
            if revision != COMMIT:
                raise ValueError(f"Source clone must use pinned revision {COMMIT}; found {revision}")
        prefix = "" if installed else "library/"
        index_bytes = reader.read(prefix + INDEX, 4 * 1024 * 1024)
        if not installed:
            # Git's Windows checkout can convert text blobs to CRLF. Pin and
            # publish the original LF form; image bytes are never normalized.
            index_bytes = index_bytes.replace(b"\r\n", b"\n")
        rows = validate_records(index_bytes)
        hashes[INDEX] = check_hash(index_bytes, INDEX_SHA256, INDEX)
        notices = {}
        for target, expected in NOTICE_HASHES.items():
            original = "LICENSE" if target == "LICENSE.upstream.txt" else target
            notices[target] = reader.read(target if installed else original, 65536)
            if not installed:
                notices[target] = notices[target].replace(b"\r\n", b"\n")
            hashes[target] = check_hash(notices[target], expected, target)
        expected_files = {INDEX, *NOTICE_HASHES, *(row[kind] for row in rows for kind in KINDS)}
        if expected_hashes is not None and set(expected_hashes) != expected_files:
            raise ValueError("Installed hairstyle hashes do not cover exactly the required library files")
        with tempfile.TemporaryDirectory(prefix="reference-gallery-hairstyle-stage-") as temporary:
            staged = Path(temporary)
            pending = []
            for row in rows:
                for kind in KINDS:
                    relative = row[kind]
                    content = reader.read(prefix + relative)
                    size = validate_png(content) if kind == "full" else webp_dimensions(content)
                    if (kind == "full" and size != (row["w"], row["h"])) or (
                            kind != "full" and (size[0] > (800 if kind == "preview" else 400)
                                                 or size[1] > (1000 if kind == "preview" else 500))):
                        raise ValueError(f"Unexpected hairstyle image dimensions: {relative}")
                    digest = hashlib.sha256(content).hexdigest()
                    if kind == "full":
                        check_hash(content, row["sha256"], relative)
                    if "hashes" in row:
                        check_hash(content, row["hashes"][kind], relative)
                    hashes[relative] = digest
                    trees[kind][Path(relative).name] = git_object("blob", content)
                    dimensions.setdefault(kind, Counter())[f"{size[0]}x{size[1]}"] += 1
                    total_bytes += len(content)
                    atomic_write(safe_path(staged, relative), content)
                    pending.append(relative)
            for kind in KINDS:
                if image_tree(trees[kind]) != IMAGE_TREES[kind]:
                    raise ValueError(f"Pinned hairstyle Git tree mismatch: {kind}")
            if expected_hashes is not None and hashes != expected_hashes:
                raise ValueError("Installed hairstyle source hashes do not match its files")
            provenance = {"url": SOURCE_URL, "revision": COMMIT, "records": len(rows),
                          "assets": len(pending), "hashes": hashes}
            for relative, content in (*notices.items(), ("SOURCE.json", (json.dumps(provenance, indent=2) + "\n").encode()),
                                      (INDEX, index_bytes)):
                atomic_write(safe_path(staged, relative), content)
            publish(staged, destination, pending + [*notices, "SOURCE.json", INDEX], INDEX)
    return {"revision": COMMIT, "records": len(rows), "images": len(pending), "image_bytes": total_bytes,
            "destination": str(destination), "dimensions": {kind: dict(counts) for kind, counts in dimensions.items()},
            "verification": "pinned index/notices SHA256, original SHA256, all image Git blob/tree hashes, PNG CRCs and PNG/WebP dimensions; no full pixel decoding"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--source", type=Path, help="Pinned clone (unrelated code edits allowed) or verified installed library; no network")
    group.add_argument("--archive", type=Path, help="Fixed-revision upstream ZIP; no network")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.source, arguments.destination, arguments.archive), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
