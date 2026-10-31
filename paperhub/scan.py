"""Read-only inventory of supported research files."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


SUPPORTED_SUFFIXES = {".pdf", ".epub", ".ppt", ".pptx", ".html", ".htm", ".mp4", ".mov"}


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    status: str
    size: Optional[int]
    md5: Optional[str]
    sha256: Optional[str]
    error: Optional[str] = None


@dataclass(frozen=True)
class ScanReport:
    items: List[FileSnapshot]
    skipped_unsupported: int


def _fingerprint(path: Path) -> FileSnapshot:
    try:
        before = path.stat()
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                md5.update(chunk)
                sha256.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ino,
        ):
            return FileSnapshot(path, "changed", after.st_size, None, None)
        return FileSnapshot(path, "stable", after.st_size, md5.hexdigest(), sha256.hexdigest())
    except OSError as exc:
        return FileSnapshot(path, "error", None, None, None, str(exc))


def scan_files(root: Path) -> List[FileSnapshot]:
    """Hash supported regular files under root without changing them."""
    return scan_directory(root).items


def scan_directory(root: Path) -> ScanReport:
    """Return supported file snapshots and the count of other regular files."""
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("scan root must be a directory, not a symlink")
    items = []
    skipped_unsupported = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if not (Path(directory) / name).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink():
                continue
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                skipped_unsupported += 1
                continue
            items.append(_fingerprint(path))
    return ScanReport(items, skipped_unsupported)
