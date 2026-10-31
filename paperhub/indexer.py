"""Incremental, non-destructive transfer of scan results into SQLite."""

from dataclasses import dataclass
import stat

from paperhub.scan import ScanReport
from paperhub.store import add_asset


@dataclass(frozen=True)
class IndexResult:
    added: int = 0
    unchanged: int = 0
    conflicts: int = 0
    retry: int = 0


def apply_scan(db, report: ScanReport) -> IndexResult:
    """Add stable paths; keep old hashes if a known path has changed."""
    added = unchanged = conflicts = retry = 0
    with db:
        for item in report.items:
            if item.status != "stable":
                retry += 1
                continue
            try:
                current_stat = item.path.lstat()
            except OSError:
                retry += 1
                continue
            if not stat.S_ISREG(current_stat.st_mode) or (
                current_stat.st_size, current_stat.st_mtime_ns, current_stat.st_ino, current_stat.st_dev
            ) != (item.size, item.mtime_ns, item.inode, item.device):
                retry += 1
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
            else:
                conflicts += 1
    return IndexResult(added, unchanged, conflicts, retry)
