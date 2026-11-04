"""Compact application card with one contextual action and an overflow menu."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QToolButton, QVBoxLayout

from ..models import ApplicationManifest, ApplicationStatus


class AppCard(QFrame):
    """Card showing identity, operational state, and state-valid actions."""

    action_clicked = Signal(str, str)

    def __init__(self, app: ApplicationManifest, archived: bool = False) -> None:
        super().__init__()
        self.app = app
        self.archived = archived
        self.current_status = ApplicationStatus.STOPPED
        self.setObjectName("card")
        self.setMinimumHeight(126)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        pixmap = QPixmap(str(app.icon))
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.title = QLabel(app.name)
        self.title.setObjectName("title")
        self.title.setToolTip(app.name)
        self.description = QLabel(app.description)
        self.description.setObjectName("description")
        self.description.setWordWrap(True)
        self.description.setMaximumHeight(38)
        self.version = QLabel(f"{app.category}  ·  v{app.version}")
        self.version.setObjectName("subtitle")
        self.status = QLabel()
        self.status.setObjectName("badge")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setMinimumWidth(88)
        self.status.setFixedHeight(24)

        self.primary_button = QPushButton()
        self.primary_button.setObjectName("primary")
        self.primary_button.setMinimumWidth(76)
        self.primary_button.setMinimumHeight(32)
        self.primary_button.clicked.connect(lambda: self.action_clicked.emit(app.id, self._primary_action()))

        self.more_button = QToolButton()
        self.more_button.setText("···")
        self.more_button.setToolTip("More actions")
        self.more_button.setAccessibleName(f"More actions for {app.name}")
        self.more_button.setMinimumSize(34, 32)
        self.more_button.clicked.connect(self._show_menu)

        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(self.icon_label)
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        text_box.addWidget(self.title)
        text_box.addWidget(self.version)
        header.addLayout(text_box, 1)
        header.addWidget(self.status)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addStretch(1)
        actions.addWidget(self.more_button)
        actions.addWidget(self.primary_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 11, 13, 11)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.description, 1)
        layout.addLayout(actions)
        self._set_archived_state(archived)

    def _primary_action(self) -> str:
        if self.archived:
            return "restore"
        if self.current_status == ApplicationStatus.RUNNING:
            return "open"
        if self.current_status == ApplicationStatus.FAILED:
            return "retry"
        return "start"

    def _show_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("View log", lambda: self.action_clicked.emit(self.app.id, "log"))
        if self.archived:
            menu.addAction("Restore", lambda: self.action_clicked.emit(self.app.id, "restore"))
        elif self.current_status == ApplicationStatus.RUNNING:
            menu.addAction("Restart", lambda: self.action_clicked.emit(self.app.id, "restart"))
            menu.addAction("Stop", lambda: self.action_clicked.emit(self.app.id, "stop"))
            menu.addSeparator()
            menu.addAction("Archive", lambda: self.action_clicked.emit(self.app.id, "archive"))
        elif self.current_status != ApplicationStatus.STARTING:
            menu.addAction("Archive", lambda: self.action_clicked.emit(self.app.id, "archive"))
        menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))

    def _set_archived_state(self, archived: bool) -> None:
        self.archived = archived
        if archived:
            self.status.setText("● Archived")
            self.primary_button.setText("Restore")
            self.primary_button.setObjectName("secondary")
        else:
            self._refresh_status()
        self.primary_button.style().unpolish(self.primary_button)
        self.primary_button.style().polish(self.primary_button)

    def set_archived(self, archived: bool) -> None:
        self._set_archived_state(archived)

    def _refresh_status(self, progress: str | None = None) -> None:
        if self.archived:
            return
        label = progress or self.current_status.value
        self.status.setText(f"● {label}")
        self.primary_button.setText({
            ApplicationStatus.RUNNING: "Open",
            ApplicationStatus.STARTING: "Starting…",
            ApplicationStatus.FAILED: "Retry",
        }.get(self.current_status, "Start"))
        self.primary_button.setEnabled(self.current_status != ApplicationStatus.STARTING)
        self.primary_button.setObjectName(
            "primary" if self.current_status == ApplicationStatus.RUNNING
            else "danger" if self.current_status == ApplicationStatus.FAILED
            else "secondary"
        )
        self.primary_button.style().unpolish(self.primary_button)
        self.primary_button.style().polish(self.primary_button)

    def set_status(self, status: ApplicationStatus, progress: str | None = None) -> None:
        self.current_status = status
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
        self._refresh_status(progress)
