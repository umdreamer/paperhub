import tempfile
import unittest
from pathlib import Path

from paperhub.scan import FileSnapshot, ScanReport, scan_directory
from paperhub.store import open_store


class IndexerTests(unittest.TestCase):
    def test_same_size_rewrite_with_restored_mtime_is_retried(self):
        import os
        from paperhub.indexer import apply_scan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "paper.pdf"
            target.write_bytes(b"old")
            report = scan_directory(root)
            before = target.stat()
            target.write_bytes(b"new")
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            with open_store(root / "index.sqlite3") as db:
                result = apply_scan(db, report)
                self.assertEqual(result.retry, 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 0)

    def _apply_scan(self):
        try:
            from paperhub.indexer import apply_scan
        except ImportError:
            self.fail("paperhub.indexer is missing")
        return apply_scan

    def test_repeated_scan_keeps_ids_and_distinct_paths(self):
        apply_scan = self._apply_scan()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.pdf").write_bytes(b"same")
            with open_store(root / "index.sqlite3") as db:
                first = apply_scan(db, scan_directory(root))
                first_id = db.execute("SELECT id FROM asset").fetchone()[0]
                again = apply_scan(db, scan_directory(root))
                self.assertEqual((first.added, again.unchanged), (1, 1))
                self.assertEqual(db.execute("SELECT id FROM asset").fetchone()[0], first_id)
                (root / "second.pdf").write_bytes(b"same")
                third = apply_scan(db, scan_directory(root))
                self.assertEqual(third.added, 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 2)

    def test_changed_path_keeps_old_digest_and_unstable_items_are_skipped(self):
        apply_scan = self._apply_scan()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "paper.pdf"
            target.write_bytes(b"original")
            with open_store(root / "index.sqlite3") as db:
                apply_scan(db, scan_directory(root))
                original = db.execute("SELECT md5, sha256 FROM asset").fetchone()
                target.write_bytes(b"changed")
                conflict = apply_scan(db, scan_directory(root))
                self.assertEqual(conflict.conflicts, 1)
                self.assertEqual(db.execute("SELECT md5, sha256 FROM asset").fetchone(), original)
                pending = ScanReport([FileSnapshot(root / "unfinished.pdf", "changed", 10, None, None)], 0)
                result = apply_scan(db, pending)
                self.assertEqual(result.retry, 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
