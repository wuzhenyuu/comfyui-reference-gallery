#!/usr/bin/env python3
"""Explicitly install optional pinned libraries; the plugin never calls this CLI."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import struct
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
MAX_ARCHIVE_BYTES = 1200 * 1024 * 1024
MAX_FILE_BYTES = 24 * 1024 * 1024


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError(f"Invalid relative path: {relative!r}")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or any(part in ("", ".", "..") for part in relative.split("/")):
        raise ValueError(f"Unsafe relative path: {relative!r}")
    resolved_root = root.resolve()
    path = (resolved_root / relative).resolve()
    if not path.is_relative_to(resolved_root):
        raise ValueError(f"Path escapes library root: {relative}")
    return path


def check_destination(destination: Path, user_environment: str) -> Path:
    destination = destination.expanduser().resolve()
    user_root = os.environ.get(user_environment)
    if user_root:
        user_root = Path(user_root).expanduser().resolve()
        if destination == user_root or destination.is_relative_to(user_root) or user_root.is_relative_to(destination):
            raise ValueError("Built-in library destination overlaps the configured user library")
    if any((destination / name).exists() for name in ("data/custom.json", "data/builtin_changes.json")):
        raise ValueError("Destination contains a user-managed library; choose a separate built-in library directory")
    return destination


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".install-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def download(urls: tuple[str, ...], destination: Path) -> None:
    errors = []
    for url in urls:
        try:
            print(f"Downloading explicitly requested library: {url}", flush=True)
            request = urllib.request.Request(url, headers={"User-Agent": "ComfyUI-Reference-Gallery-Installer/1"})
            total = 0
            with urllib.request.urlopen(request, timeout=90) as response, destination.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ValueError("Archive exceeds size limit")
                    output.write(chunk)
            if not zipfile.is_zipfile(destination):
                raise ValueError("Downloaded file is not a ZIP archive")
            print(f"Downloaded {total} bytes", flush=True)
            return
        except (OSError, ValueError, urllib.error.URLError) as error:
            errors.append(f"{url}: {error}")
            destination.unlink(missing_ok=True)
    raise RuntimeError("Archive sources failed:\n" + "\n".join(errors))


class DirectorySource:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)

    def read(self, relative: str, limit: int = MAX_FILE_BYTES) -> bytes:
        path = safe_path(self.root, relative)
        if not path.is_file() or path.stat().st_size > limit:
            raise ValueError(f"Missing or oversized source file: {relative}")
        return path.read_bytes()

    def exists(self, relative: str) -> bool:
        return safe_path(self.root, relative).is_file()

    def verify_clone(self, commit: str) -> None:
        if not (self.root / ".git").exists():
            raise ValueError("Source is neither a recorded installed library nor a Git clone")
        revision = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
        if revision != commit:
            raise ValueError(f"Clone revision must be exactly {commit}; found {revision}")
        changed = subprocess.check_output(["git", "-C", str(self.root), "status", "--porcelain", "--untracked-files=no"], text=True)
        if changed.strip():
            raise ValueError("Source clone has modified tracked files; use a clean pinned checkout")


class ZipSource:
    def __init__(self, archive: zipfile.ZipFile, prefix: str):
        self.archive = archive
        self.prefix = prefix

    def read(self, relative: str, limit: int = MAX_FILE_BYTES) -> bytes:
        # Constructed whitelist names only. No extract/extractall is used.
        safe_path(Path(tempfile.gettempdir()), relative)
        name = self.prefix + relative
        matches = [entry for entry in self.archive.infolist() if entry.filename == name]
        if len(matches) != 1 or matches[0].is_dir() or matches[0].file_size > limit:
            raise ValueError(f"Missing, duplicate or oversized archive entry: {relative}")
        if (matches[0].external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError(f"Archive symlink rejected: {relative}")
        return self.archive.read(matches[0])


@contextmanager
def open_input(source: Path | None, archive: Path | None, urls: tuple[str, ...], prefix: str):
    if source is not None:
        yield DirectorySource(source)
    elif archive is not None:
        with zipfile.ZipFile(archive) as zipped:
            yield ZipSource(zipped, prefix)
    else:
        with tempfile.TemporaryDirectory(prefix="reference-gallery-download-") as temporary:
            path = Path(temporary) / "upstream.zip"
            download(urls, path)
            with zipfile.ZipFile(path) as zipped:
                yield ZipSource(zipped, prefix)


def publish(staged: Path, destination: Path, relative_files: list[str], last: str) -> None:
    # Resolve and validate every target before publishing any file. Never sweep
    # or delete unrelated files. The complete index is always replaced last.
    ordered = [name for name in relative_files if name != last] + [last]
    targets = [(safe_path(staged, name), safe_path(destination, name)) for name in ordered]
    for source, target in targets:
        content = source.read_bytes()
        if not target.is_file() or target.read_bytes() != content:
            atomic_write(target, content)


def validate_png(content: bytes) -> tuple[int, int]:
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid PNG signature")
    offset, dimensions, ended = 8, None, False
    while offset + 12 <= len(content):
        length = struct.unpack_from(">I", content, offset)[0]
        kind = content[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(content):
            raise ValueError("Truncated PNG chunk")
        data = content[offset + 8:offset + 8 + length]
        if zlib.crc32(kind + data) & 0xFFFFFFFF != struct.unpack_from(">I", content, offset + 8 + length)[0]:
            raise ValueError("PNG CRC mismatch")
        if offset == 8:
            if kind != b"IHDR" or length != 13:
                raise ValueError("Invalid PNG IHDR")
            dimensions = struct.unpack_from(">II", data)
        offset = end
        if kind == b"IEND":
            ended = length == 0 and offset == len(content)
            break
    if not ended or not dimensions or not all(0 < value <= 16384 for value in dimensions):
        raise ValueError("Incomplete PNG or invalid dimensions")
    return dimensions


def validate_jpeg(content: bytes) -> tuple[int, int]:
    if not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
        raise ValueError("Invalid JPEG framing")
    offset = 2
    while offset + 4 <= len(content):
        if content[offset] != 255:
            raise ValueError("Invalid JPEG segment")
        while offset < len(content) and content[offset] == 255:
            offset += 1
        marker = content[offset]
        offset += 1
        if marker in (0x01, *range(0xD0, 0xDA)):
            continue
        length = int.from_bytes(content[offset:offset + 2], "big")
        if length < 2 or offset + length > len(content):
            raise ValueError("Invalid JPEG segment length")
        if marker in (0xC0, 0xC1, 0xC2):
            if length < 8:
                raise ValueError("Invalid JPEG SOF")
            height, width = struct.unpack_from(">HH", content, offset + 3)
            if not all(0 < value <= 16384 for value in (width, height)):
                raise ValueError("Invalid JPEG dimensions")
            return width, height
        if marker == 0xDA:
            break
        offset += length
    raise ValueError("JPEG has no supported frame header")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", choices=("all", "pose", "costume"), default="all")
    parser.add_argument("--source", type=Path, help="Offline source for a single selected library")
    parser.add_argument("--pose-source", type=Path, help="Offline pose clone or installed library")
    parser.add_argument("--costume-source", type=Path, help="Offline costume clone or installed library")
    parser.add_argument("--destination", type=Path, help="Selected library target; for all, the bundle root")
    arguments = parser.parse_args()
    if arguments.source and arguments.library == "all":
        parser.error("For all, use --pose-source and --costume-source")
    selected = ("pose", "costume") if arguments.library == "all" else (arguments.library,)
    reports = {}
    for kind in selected:
        if kind == "pose":
            from install_pose_library import run
            source = arguments.pose_source
        else:
            from install_costume_library import run
            source = arguments.costume_source
        destination = arguments.destination
        if destination and arguments.library == "all":
            destination = destination / kind / "library"
        reports[kind] = run(source=arguments.source or source, destination=destination)
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
