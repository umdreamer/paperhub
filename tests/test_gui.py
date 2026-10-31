import tempfile
import time
import unittest
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this Python environment")
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _window(self):
        try:
            from paperhub.gui import MainWindow
        except ImportError:
            self.fail("paperhub.gui is missing")
        return MainWindow()

    def test_manual_scan_shows_indexed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "library"
            root.mkdir()
            (root / "paper.pdf").write_bytes(b"paper")
            window = self._window()
            window.library_edit.setText(str(root))
            window.database_edit.setText(str(Path(directory) / "index.sqlite3"))
            window.scan_button.click()
            deadline = time.monotonic() + 5
            while not window.scan_button.isEnabled() and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertTrue(window.scan_button.isEnabled())
            self.assertIn("新增 1", window.status_label.text())
            self.assertEqual(window.table.rowCount(), 1)
            self.assertIn("paper.pdf", window.table.item(0, 0).text())
            window.close()

    def test_invalid_directory_is_visible_without_creating_database(self):
        with tempfile.TemporaryDirectory() as directory:
            window = self._window()
            database = Path(directory) / "index.sqlite3"
            window.library_edit.setText(str(Path(directory) / "missing"))
            window.database_edit.setText(str(database))
            window.scan_button.click()
            self.app.processEvents()
            self.assertIn("错误", window.status_label.text())
            self.assertFalse(database.exists())
            window.close()

    def test_blank_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            window = self._window()
            database = Path(directory) / "index.sqlite3"
            window.library_edit.setText("   ")
            window.database_edit.setText(str(database))
            window.scan_button.click()
            self.app.processEvents()
            self.assertIn("错误", window.status_label.text())
            self.assertFalse(database.exists())
            window.close()
