import tempfile
import unittest
import sqlite3
import hashlib
from pathlib import Path


class StoreTests(unittest.TestCase):
    def _api(self):
        try:
            from paperhub.store import add_asset, add_work, link_asset, link_zotero, open_store
        except ImportError:
            self.fail("store relationship API is missing")
        return add_asset, add_work, link_asset, link_zotero, open_store

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

    def test_work_and_asset_relationship_is_many_to_many(self):
        add_asset, add_work, link_asset, _, open_store = self._api()
        with tempfile.TemporaryDirectory() as directory:
            with open_store(Path(directory) / "index.sqlite3") as db:
                first_work = add_work(db, "paper", "Example")
                second_work = add_work(db, "presentation", "Talk")
                first_asset = add_asset(db, "/library/paper.pdf", 3, "a" * 32, "b" * 64)
                second_asset = add_asset(db, "/library/slides.pptx", 4, "c" * 32, "d" * 64)
                link_asset(db, first_work, first_asset, "main")
                link_asset(db, first_work, second_asset, "slides")
                link_asset(db, second_work, second_asset, "main")
                rows = db.execute("SELECT work_id, asset_id, role FROM work_asset").fetchall()
                self.assertEqual(len(rows), 3)

    def test_unique_path_and_zotero_item_key(self):
        add_asset, add_work, _, link_zotero, open_store = self._api()
        with tempfile.TemporaryDirectory() as directory:
            with open_store(Path(directory) / "index.sqlite3") as db:
                work = add_work(db, "paper")
                add_asset(db, "/library/item.pdf", 3, "a" * 32, "b" * 64)
                with self.assertRaises(sqlite3.IntegrityError):
                    add_asset(db, "/library/item.pdf", 3, "a" * 32, "b" * 64)
                link_zotero(db, work, "user-1", "ABCD1234")
                with self.assertRaises(sqlite3.IntegrityError):
                    link_zotero(db, work, "user-1", "ABCD1234")

    def test_missing_title_stays_null_and_same_hash_can_have_two_paths(self):
        add_asset, add_work, _, _, open_store = self._api()
        with tempfile.TemporaryDirectory() as directory:
            with open_store(Path(directory) / "index.sqlite3") as db:
                work = add_work(db, "book")
                add_asset(db, "/source/book.pdf", 3, "a" * 32, "b" * 64)
                add_asset(db, "/archive/book.pdf", 3, "a" * 32, "b" * 64)
                self.assertIsNone(db.execute("SELECT title FROM work WHERE id = ?", (work,)).fetchone()[0])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 2)

    def test_paperhub_database_has_nonzero_application_id(self):
        from paperhub.store import open_store

        with tempfile.TemporaryDirectory() as directory:
            with open_store(Path(directory) / "index.sqlite3") as db:
                self.assertNotEqual(db.execute("PRAGMA application_id").fetchone()[0], 0)

    def test_unrelated_existing_database_is_not_modified(self):
        from paperhub.store import open_store

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "other.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE private_data (value TEXT)")
                db.execute("INSERT INTO private_data VALUES ('keep')")
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                open_store(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT value FROM private_data").fetchone()[0], "keep")
                self.assertIsNone(
                    db.execute("SELECT name FROM sqlite_master WHERE name = 'asset'").fetchone()
                )


if __name__ == "__main__":
    unittest.main()
