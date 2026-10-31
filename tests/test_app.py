import tempfile
import unittest
from pathlib import Path

from paperhub.store import open_store


class AppControllerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
