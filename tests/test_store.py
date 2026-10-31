import tempfile
import unittest
from pathlib import Path


class StoreTests(unittest.TestCase):
    def test_database_reopens_with_work_and_foreign_keys(self):
        try:
            from paperhub.store import open_store
        except ModuleNotFoundError:
            self.fail("paperhub.store is missing")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.sqlite3"
            with open_store(path) as db:
                self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                db.execute(
                    "INSERT INTO work (id, kind, title) VALUES (?, ?, ?)",
                    ("work-1", "paper", "Example"),
                )
            with open_store(path) as db:
                row = db.execute("SELECT kind, title FROM work WHERE id = ?", ("work-1",)).fetchone()
                self.assertEqual(row, ("paper", "Example"))


if __name__ == "__main__":
    unittest.main()
