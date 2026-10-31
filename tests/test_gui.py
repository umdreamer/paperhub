import tempfile
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_close_waits_for_running_scan_thread(self):
        from paperhub.indexer import IndexResult
        from paperhub.scan import ScanReport

        with tempfile.TemporaryDirectory() as directory:
            started = threading.Event()
            release = threading.Event()

            def slow_scan(*_args):
                started.set()
                release.wait(3)
                return ScanReport([], 0), IndexResult()

            window = self._window()
            window.library_edit.setText(directory)
            window.database_edit.setText(str(Path(directory) / "index.sqlite3"))
            window.show()
            try:
                with patch("paperhub.gui.run_scan", side_effect=slow_scan):
                    window.scan_button.click()
                    deadline = time.monotonic() + 3
                    while not started.is_set() and time.monotonic() < deadline:
                        self.app.processEvents()
                        time.sleep(0.01)
                    self.assertTrue(started.is_set())
                    window.close()
                    stayed_open = window.isVisible()
                    release.set()
                    while not window.scan_button.isEnabled() and time.monotonic() < deadline:
                        self.app.processEvents()
                        time.sleep(0.01)
                self.assertTrue(window.scan_button.isEnabled())
                self.assertTrue(stayed_open)
                window.close()
                self.assertFalse(window.isVisible())
            finally:
                release.set()

    def test_changed_file_row_is_labeled_as_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "paper.pdf"
            target.write_bytes(b"first")
            window = self._window()
            window.library_edit.setText(directory)
            window.database_edit.setText(str(Path(directory) / "index.sqlite3"))
            for content in (b"first", b"changed content"):
                target.write_bytes(content)
                window.scan_button.click()
                deadline = time.monotonic() + 5
                while not window.scan_button.isEnabled() and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.01)
            self.assertIn("冲突", window.table.item(0, 1).text())
            self.assertIn("本次扫描", window.table.horizontalHeaderItem(3).text())
            window.close()
