"""Qt desktop view for manual, read-only library inventory."""

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from paperhub.app import run_scan


class ScanWorker(QObject):
    completed = Signal(object, object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, library: Path, database: Path):
        super().__init__()
        self.library = library
        self.database = database

    @Slot()
    def run(self):
        try:
            report, result = run_scan(self.library, self.database)
            self.completed.emit(report, result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self, library=None, database=None):
        super().__init__()
        self.setWindowTitle("PaperHub · 本地资料索引")
        self.resize(1100, 650)
        self._thread = None
        self._worker = None

        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.library_edit = QLineEdit(str(library or ""))
        self.database_edit = QLineEdit(str(database or ""))
        for label, entry, handler in (
            ("资料目录", self.library_edit, self._choose_library),
            ("SQLite 索引", self.database_edit, self._choose_database),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(entry)
            choose = QPushButton("选择…")
            choose.clicked.connect(handler)
            row.addWidget(choose)
            layout.addLayout(row)

        self.scan_button = QPushButton("扫描并更新索引")
        self.scan_button.clicked.connect(self.start_scan)
        layout.addWidget(self.scan_button)
        self.status_label = QLabel("请选择资料目录和索引文件，然后手动扫描。")
        layout.addWidget(self.status_label)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["路径", "状态", "字节数", "MD5", "SHA-256"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.setCentralWidget(panel)

    def _choose_library(self):
        selected = QFileDialog.getExistingDirectory(self, "选择资料目录")
        if selected:
            self.library_edit.setText(selected)

    def _choose_database(self):
        selected, _ = QFileDialog.getSaveFileName(
            self, "选择 SQLite 索引文件", "paperhub.sqlite3", "SQLite (*.sqlite3)"
        )
        if selected:
            self.database_edit.setText(selected)

    def start_scan(self):
        library = Path(self.library_edit.text().strip())
        database_text = self.database_edit.text().strip()
        if not library.is_dir() or library.is_symlink() or not database_text:
            self.status_label.setText("错误：请选择有效资料目录和 SQLite 索引文件。")
            return
        database = Path(database_text)
        if not database.parent.is_dir():
            self.status_label.setText("错误：索引文件的上级目录不存在。")
            return

        self.scan_button.setEnabled(False)
        self.status_label.setText("正在扫描…")
        self._thread = QThread(self)
        self._worker = ScanWorker(library, database)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.completed.connect(self._show_result)
        self._worker.failed.connect(self._show_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._scan_done)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @Slot(object, object)
    def _show_result(self, report, result):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(report.items))
        for row, item in enumerate(report.items):
            values = (str(item.path), item.status, str(item.size or 0), item.md5 or "", item.sha256 or "")
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.setUpdatesEnabled(True)
        self.status_label.setText(
            f"新增 {result.added} · 未变 {result.unchanged} · 冲突 {result.conflicts} · 待重试 {result.retry} · 不支持 {report.skipped_unsupported}"
        )
        self.status_label.setStyleSheet("color: #b00020;" if result.conflicts else "")

    @Slot(str)
    def _show_error(self, message):
        self.status_label.setText(f"错误：{message}")

    @Slot()
    def _scan_done(self):
        self.scan_button.setEnabled(True)
        self._worker = None
        self._thread = None


def launch_gui(library=None, database=None):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(library, database)
    window.show()
    return app.exec()
