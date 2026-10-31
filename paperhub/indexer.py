"""Incremental, non-destructive transfer of scan results into SQLite."""

from dataclasses import dataclass
import stat
from pathlib import Path
from typing import Tuple

from paperhub.scan import ScanReport
from paperhub.store import add_asset


@dataclass(frozen=True)
class IndexResult:
    added: int = 0
    unchanged: int = 0
    conflicts: int = 0
    retry: int = 0
    missing: int = 0
    conflict_paths: Tuple[str, ...] = ()
    retry_paths: Tuple[str, ...] = ()


def apply_scan(db, report: ScanReport) -> IndexResult:
    """Add stable paths; keep old hashes if a known path has changed."""
    added = unchanged = conflicts = retry = 0
    seen_paths = {str(item.path) for item in report.items}
    conflict_paths = []
    retry_paths = []
    with db:
        for item in report.items:
            if item.status != "stable":
                retry += 1
                retry_paths.append(str(item.path))
                continue
            try:
                current_stat = item.path.lstat()
            except OSError:
                retry += 1
                retry_paths.append(str(item.path))
                continue
            if not stat.S_ISREG(current_stat.st_mode) or (
                current_stat.st_size, current_stat.st_mtime_ns, current_stat.st_ino, current_stat.st_dev, current_stat.st_ctime_ns
            ) != (item.size, item.mtime_ns, item.inode, item.device, item.ctime_ns):
                retry += 1
                retry_paths.append(str(item.path))
                continue
            previous = db.execute(
                "SELECT size, md5, sha256 FROM asset WHERE path = ?", (str(item.path),)
            ).fetchone()
            current = (item.size, item.md5, item.sha256)
            if previous is None:
                add_asset(db, str(item.path), item.size, item.md5, item.sha256)
                added += 1
            elif previous == current:
                unchanged += 1
                db.execute("UPDATE asset SET status = 'present' WHERE path = ?", (str(item.path),))
            else:
                conflicts += 1
                conflict_paths.append(str(item.path))
        missing = 0
        if report.root is not None:
            for path, status in db.execute("SELECT path, status FROM asset").fetchall():
                file_path = Path(path)
                if not file_path.is_relative_to(report.root):
                    continue
                if path not in seen_paths and not file_path.exists() and status != "missing":
                    db.execute("UPDATE asset SET status = 'missing' WHERE path = ?", (path,))
                    status = "missing"
                if status == "missing":
                    missing += 1
    return IndexResult(added, unchanged, conflicts, retry, missing, tuple(conflict_paths), tuple(retry_paths))
