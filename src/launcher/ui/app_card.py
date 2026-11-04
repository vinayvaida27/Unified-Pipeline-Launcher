"""Application card widget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..models import ApplicationManifest, ApplicationStatus


class AppCard(QFrame):
    """Card showing one application and actions."""

    open_clicked = Signal(str)
    stop_clicked = Signal(str)
    restart_clicked = Signal(str)
    log_clicked = Signal(str)

    def __init__(self, app: ApplicationManifest) -> None:
        super().__init__()
        self.app = app
        self.setObjectName("card")
        self.setMinimumHeight(142)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(46, 46)
        pixmap = QPixmap(str(app.icon))
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap.scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.title = QLabel(app.name)
        self.title.setObjectName("title")
        self.description = QLabel(app.description)
        self.description.setObjectName("description")
        self.description.setWordWrap(True)
        self.version = QLabel(f"{app.category}  |  Version {app.version}")
        self.version.setObjectName("subtitle")
        self.status = QLabel(ApplicationStatus.STOPPED.value)
        self.status.setObjectName("badge")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setMinimumWidth(112)
        self.open_button = QPushButton("Open")
        self.stop_button = QPushButton("Stop")
        self.restart_button = QPushButton("Restart")
        self.log_button = QPushButton("View Log")
        for button in (self.open_button, self.stop_button, self.restart_button, self.log_button):
            button.setMinimumWidth(78)
        for button in (self.stop_button, self.restart_button, self.log_button):
            button.setObjectName("secondary")
        self.stop_button.setEnabled(False)
        self.restart_button.setEnabled(False)
        self.open_button.clicked.connect(lambda: self.open_clicked.emit(app.id))
        self.stop_button.clicked.connect(lambda: self.stop_clicked.emit(app.id))
        self.restart_button.clicked.connect(lambda: self.restart_clicked.emit(app.id))
        self.log_button.clicked.connect(lambda: self.log_clicked.emit(app.id))

        header = QHBoxLayout()
        header.addWidget(self.icon_label)
        text_box = QVBoxLayout()
        text_box.addWidget(self.title)
        text_box.addWidget(self.version)
        header.addLayout(text_box, 1)
        header.addWidget(self.status)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.log_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.restart_button)
        actions.addWidget(self.open_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.description, 1)
        layout.addLayout(actions)

    def set_status(self, status: ApplicationStatus, progress: str | None = None) -> None:
        """Update status text and button state."""

        label = progress or status.value
        self.status.setText(label)
        if status == ApplicationStatus.RUNNING:
            self.status.setObjectName("badgeRunning")
        elif status == ApplicationStatus.STARTING:
            self.status.setObjectName("badgeStarting")
        elif status == ApplicationStatus.FAILED:
            self.status.setObjectName("badgeFailed")
        else:
            self.status.setObjectName("badge")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        starting = status == ApplicationStatus.STARTING
        running = status == ApplicationStatus.RUNNING
        self.open_button.setEnabled(not starting)
        self.stop_button.setEnabled(running or starting)
        self.restart_button.setEnabled(running)
