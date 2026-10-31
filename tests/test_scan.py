import hashlib
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
