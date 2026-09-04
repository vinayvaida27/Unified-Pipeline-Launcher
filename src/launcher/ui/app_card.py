"""Application card widget."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

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
        self.setProperty("state", "stopped")
        self.setFixedHeight(142)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(app.icon))
        if not pixmap.isNull():
            self.icon_label.setPixmap(
                pixmap.scaled(
                    40,
                    40,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.icon_label.setObjectName("appIconFallback")
            self.icon_label.setText(app.name[:1].upper())
        self.title = QLabel(app.name)
        self.title.setObjectName("appTitle")
        self.title.setWordWrap(True)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.description = QLabel(app.description)
        self.description.setObjectName("description")
        self.description.setWordWrap(True)
        self.description.setMaximumHeight(34)
        self.description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.version = QLabel(f"{app.category}  |  Version {app.version}")
        self.version.setObjectName("appMeta")
        self.version.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.status = QLabel(ApplicationStatus.STOPPED.value)
        self.status.setObjectName("badge")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFixedSize(88, 28)
        self.open_button = QPushButton("Open")
        self.stop_button = QPushButton("Stop")
        self.restart_button = QPushButton("Restart")
        self.log_button = QPushButton("Logs")
        self.open_button.setObjectName("primary")
        self.stop_button.setObjectName("danger")
        self.restart_button.setObjectName("secondary")
        self.log_button.setObjectName("quiet")
        for button, width in (
            (self.log_button, 64),
            (self.stop_button, 68),
            (self.restart_button, 82),
            (self.open_button, 86),
        ):
            button.setFixedSize(width, 34)
        self.open_button.setToolTip(f"Open {app.name}")
        self.stop_button.setToolTip(f"Stop {app.name}")
        self.restart_button.setToolTip(f"Restart {app.name}")
        self.log_button.setToolTip(f"View logs for {app.name}")
        self.stop_button.setAccessibleName(f"Stop {app.name}")
        self.restart_button.setAccessibleName(f"Restart {app.name}")
        self.log_button.setAccessibleName(f"View logs for {app.name}")
        self.open_button.clicked.connect(lambda: self.open_clicked.emit(app.id))
        self.stop_button.clicked.connect(lambda: self.stop_clicked.emit(app.id))
        self.restart_button.clicked.connect(lambda: self.restart_clicked.emit(app.id))
        self.log_button.clicked.connect(lambda: self.log_clicked.emit(app.id))

        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(self.icon_label)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.addWidget(self.title)
        text_box.addWidget(self.version)
        header.addLayout(text_box, 1)
        header.addWidget(self.status, 0, Qt.AlignmentFlag.AlignTop)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addStretch(1)
        actions.addWidget(self.log_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.restart_button)
        actions.addWidget(self.open_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 12)
        layout.setSpacing(7)
        layout.addLayout(header)
        layout.addWidget(self.description, 1, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(actions)
        self.set_status(ApplicationStatus.STOPPED)

    def set_status(self, status: ApplicationStatus, progress: str | None = None) -> None:
        """Update status text and button state."""

        detail = progress or status.value
        label = "Queued" if progress == "Queued" else status.value
        self.status.setText(label)
        self.status.setToolTip(detail)
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
        self.setProperty("state", status.value.lower())
        self.style().unpolish(self)
        self.style().polish(self)
        starting = status == ApplicationStatus.STARTING
        running = status == ApplicationStatus.RUNNING
        self.open_button.setText("View" if running else "Open")
        self.open_button.setEnabled(not starting)
        self.stop_button.setVisible(running or starting)
        self.stop_button.setEnabled(running or starting)
        self.restart_button.setVisible(running)
        self.restart_button.setEnabled(running)
