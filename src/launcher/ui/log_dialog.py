"""Log viewer dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout


class LogDialog(QDialog):
    """Simple read-only log viewer."""

    def __init__(self, log_path: Path | None, parent=None) -> None:
        super().__init__(parent)
        self.log_path = log_path
        self.setWindowTitle("Application Log")
        self.resize(900, 560)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        self.refresh()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

    def refresh(self) -> None:
        """Refresh the visible log content."""

        if self.log_path and self.log_path.exists():
            self.text.setPlainText(self.log_path.read_text(encoding="utf-8", errors="replace")[-120000:])
            self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())
        else:
            self.text.setPlainText("No log file is available yet.")
