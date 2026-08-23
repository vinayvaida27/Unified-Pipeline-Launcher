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
    QStyle,
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
        self.setMinimumHeight(154)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(44, 44)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(app.icon))
        if not pixmap.isNull():
            self.icon_label.setPixmap(
                pixmap.scaled(
                    44,
                    44,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        self.title = QLabel(app.name)
        self.title.setObjectName("appTitle")
        self.title.setWordWrap(True)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.description = QLabel(app.description)
        self.description.setObjectName("description")
        self.description.setWordWrap(True)
        self.description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.version = QLabel(f"{app.category}  |  Version {app.version}")
        self.version.setObjectName("appMeta")
        self.version.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.status = QLabel(ApplicationStatus.STOPPED.value)
        self.status.setObjectName("badge")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFixedWidth(132)
        self.open_button = QPushButton("Open")
        self.stop_button = QPushButton()
        self.restart_button = QPushButton()
        self.log_button = QPushButton()
        self.open_button.setObjectName("primary")
        self.stop_button.setObjectName("dangerIcon")
        self.restart_button.setObjectName("toolIcon")
        self.log_button.setObjectName("toolIcon")
        self.open_button.setFixedWidth(98)
        for button in (self.stop_button, self.restart_button, self.log_button):
            button.setFixedWidth(40)
        self.open_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.restart_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.log_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.open_button.setToolTip(f"Open {app.name}")
        self.stop_button.setToolTip(f"Stop {app.name}")
        self.restart_button.setToolTip(f"Restart {app.name}")
        self.log_button.setToolTip(f"View logs for {app.name}")
        self.stop_button.setAccessibleName(f"Stop {app.name}")
        self.restart_button.setAccessibleName(f"Restart {app.name}")
        self.log_button.setAccessibleName(f"View logs for {app.name}")
        self.stop_button.setEnabled(False)
        self.restart_button.setEnabled(False)
        self.open_button.clicked.connect(lambda: self.open_clicked.emit(app.id))
        self.stop_button.clicked.connect(lambda: self.stop_clicked.emit(app.id))
        self.restart_button.clicked.connect(lambda: self.restart_clicked.emit(app.id))
        self.log_button.clicked.connect(lambda: self.log_clicked.emit(app.id))

        header = QHBoxLayout()
        header.addWidget(self.icon_label)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.addWidget(self.title)
        text_box.addWidget(self.version)
        header.addLayout(text_box, 1)
        header.addWidget(self.status)

        actions = QHBoxLayout()
        actions.setSpacing(7)
        actions.addStretch(1)
        actions.addWidget(self.log_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.restart_button)
        actions.addWidget(self.open_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 15, 16, 14)
        layout.setSpacing(9)
        layout.addLayout(header)
        layout.addWidget(self.description, 1)
        layout.addLayout(actions)

    def set_status(self, status: ApplicationStatus, progress: str | None = None) -> None:
        """Update status text and button state."""

        label = progress or status.value
        self.status.setText(self.status.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, 116))
        self.status.setToolTip(label)
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
        self.open_button.setText("View" if running else "Open")
        self.open_button.setEnabled(not starting)
        self.stop_button.setEnabled(running or starting)
        self.restart_button.setEnabled(running)
