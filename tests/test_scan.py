import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ScanTests(unittest.TestCase):
    def test_nested_supported_files_get_both_hashes_without_following_links(self):
        try:
            from paperhub.scan import scan_files
        except ImportError:
            self.fail("paperhub.scan is missing")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "topic"
            nested.mkdir()
            data = b"example-content"
            names = ["paper.pdf", "book.epub", "deck.pptx", "page.html", "video.mp4"]
            for name in names:
                (nested / name).write_bytes(data)
            (nested / "note.txt").write_bytes(data)
            (root / "linked.pdf").symlink_to(nested / "paper.pdf")

            items = scan_files(root)

            self.assertEqual({item.path.name for item in items}, set(names))
            for item in items:
                self.assertEqual(item.status, "stable")
                self.assertEqual(item.size, len(data))
                self.assertEqual(item.md5, hashlib.md5(data).hexdigest())
                self.assertEqual(item.sha256, hashlib.sha256(data).hexdigest())
            self.assertEqual((nested / "paper.pdf").read_bytes(), data)

    def test_report_counts_unsupported_files(self):
        try:
            from paperhub.scan import scan_directory
        except ImportError:
            self.fail("scan_directory is missing")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "paper.pdf").write_bytes(b"paper")
            (root / "notes.txt").write_bytes(b"notes")
            report = scan_directory(root)
            self.assertEqual(len(report.items), 1)
            self.assertEqual(report.skipped_unsupported, 1)

    def test_file_changed_during_hash_is_marked_for_retry(self):
        from paperhub.scan import scan_files

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "paper.pdf"
            target.write_bytes(b"original")
            original_md5 = hashlib.md5

            class ChangingHash:
                def __init__(self):
                    self.inner = original_md5()

                def update(self, chunk):
                    self.inner.update(chunk)
                    target.write_bytes(b"new content")

                def hexdigest(self):
                    return self.inner.hexdigest()

            with patch("paperhub.scan.hashlib.md5", side_effect=ChangingHash):
                items = scan_files(root)
            self.assertEqual(items[0].status, "changed")
            self.assertIsNone(items[0].md5)


if __name__ == "__main__":
    unittest.main()
