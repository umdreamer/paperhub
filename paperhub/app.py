"""User-facing scan controller for the local PaperHub index."""

from pathlib import Path

from paperhub.indexer import apply_scan
from paperhub.scan import scan_directory
from paperhub.store import open_store


def run_scan(root: Path, database: Path):
    """Scan a chosen directory and apply stable results to a chosen database."""
    if not str(root).strip():
        raise ValueError("library directory is blank")
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("library directory does not exist or is a symlink")
    report = scan_directory(root)
    db = open_store(database)
    try:
        result = apply_scan(db, report)
    finally:
        db.close()
    return report, result
