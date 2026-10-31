import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

from paperhub.store import open_store


class AppControllerTests(unittest.TestCase):
    def test_different_content_reappearing_is_conflict_not_missing(self):
        from paperhub.app import run_scan

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            library = base / "library"
            library.mkdir()
            target = library / "paper.pdf"
            target.write_bytes(b"old")
            database = base / "index.sqlite3"
            run_scan(library, database)
            target.rename(base / "retained.pdf")
            run_scan(library, database)
            target.write_bytes(b"new content")
            _, result = run_scan(library, database)
            self.assertEqual((result.conflicts, result.missing), (1, 0))
            with open_store(database) as db:
                self.assertEqual(db.execute("SELECT status FROM asset").fetchone()[0], "conflict")

    def test_module_help_explains_manual_scan(self):
        result = subprocess.run(
            [sys.executable, "-m", "paperhub", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PaperHub", result.stdout)
        self.assertIn("--library", result.stdout)

    def _run_scan(self):
        try:
            from paperhub.app import run_scan
        except ImportError:
            self.fail("paperhub.app is missing")
        return run_scan

    def test_manual_scan_persists_and_repeated_scan_is_unchanged(self):
        run_scan = self._run_scan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "library"
            root.mkdir()
            (root / "paper.pdf").write_bytes(b"paper")
            database = Path(directory) / "index.sqlite3"
            first_report, first_result = run_scan(root, database)
            second_report, second_result = run_scan(root, database)
            self.assertEqual(len(first_report.items), 1)
            self.assertEqual((first_result.added, second_result.unchanged), (1, 1))
            self.assertEqual(len(second_report.items), 1)
            with open_store(database) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 1)

    def test_invalid_root_does_not_create_database(self):
        run_scan = self._run_scan()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "index.sqlite3"
            with self.assertRaises(ValueError):
                run_scan(Path(directory) / "missing", database)
            self.assertFalse(database.exists())

    def test_blank_root_does_not_scan_current_directory(self):
        run_scan = self._run_scan()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "index.sqlite3"
            for blank in ("", "   "):
                with self.assertRaises(ValueError):
                    run_scan(blank, database)
            self.assertFalse(database.exists())

    def test_file_changed_after_scan_is_not_indexed_with_old_hash(self):
        from paperhub.app import run_scan
        from paperhub.scan import scan_directory

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "library"
            root.mkdir()
            target = root / "paper.pdf"
            target.write_bytes(b"original")
            database = Path(directory) / "index.sqlite3"

            def change_after_scan(selected_root):
                report = scan_directory(selected_root)
                target.write_bytes(b"changed after scan")
                return report

            with patch("paperhub.app.scan_directory", side_effect=change_after_scan):
                _, result = run_scan(root, database)
            self.assertEqual(result.retry, 1)
            with open_store(database) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 0)

    def test_moved_file_is_marked_missing_without_losing_old_hash(self):
        from paperhub.app import run_scan

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            library = base / "library"
            other = base / "other"
            library.mkdir()
            other.mkdir()
            source = library / "paper.pdf"
            source.write_bytes(b"paper")
            (other / "book.epub").write_bytes(b"book")
            database = base / "index.sqlite3"
            run_scan(library, database)
            run_scan(other, database)
            with open_store(database) as db:
                old_id, old_hash = db.execute(
                    "SELECT id, sha256 FROM asset WHERE path = ?", (str(source),)
                ).fetchone()
            moved = other / "moved.pdf"
            source.rename(moved)
            _, result = run_scan(library, database)
            self.assertEqual(getattr(result, "missing", 0), 1)
            with open_store(database) as db:
                self.assertEqual(
                    db.execute("SELECT id, sha256, status FROM asset WHERE path = ?", (str(source),)).fetchone(),
                    (old_id, old_hash, "missing"),
                )
                self.assertNotEqual(
                    db.execute("SELECT status FROM asset WHERE path = ?", (str(other / "book.epub"),)).fetchone()[0],
                    "missing",
                )
            moved.rename(source)
            _, restored = run_scan(library, database)
            self.assertEqual(getattr(restored, "missing", 0), 0)
            with open_store(database) as db:
                self.assertEqual(
                    db.execute("SELECT id, status FROM asset WHERE path = ?", (str(source),)).fetchone(),
                    (old_id, "present"),
                )


if __name__ == "__main__":
    unittest.main()
