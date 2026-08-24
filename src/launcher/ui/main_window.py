"""Main launcher window."""

from __future__ import annotations

from collections import deque
import logging
import os
from threading import Event
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import uuid4

from PySide6.QtCore import Qt, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..environment_manager import EnvironmentManager
from ..health_checker import HealthChecker
from ..models import ApplicationManifest, ApplicationStatus, PlatformConfig
from ..process_manager import ProcessManager
from ..secure_browser import open_isolated_browser
from .about_dialog import show_about
from .app_card import AppCard
from .log_dialog import LogDialog
from .settings_dialog import SettingsDialog
from .styles import APP_STYLE
from .workers import Worker

LOG = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary PySide6 application window."""

    def __init__(
        self,
        config: PlatformConfig,
        apps: list[ApplicationManifest],
        environment_manager: EnvironmentManager,
        process_manager: ProcessManager,
    ) -> None:
        super().__init__()
        self.config = config
        self.apps = apps
        self.environment_manager = environment_manager
        self.process_manager = process_manager
        self.cards: dict[str, AppCard] = {}
        self._filtered_app_ids = [app.id for app in apps]
        self._column_count = 0
        self._startup_queue: deque[str] = deque()
        self._queued_ids: set[str] = set()
        self._starting_ids: set[str] = set()
        self._launch_tokens: dict[str, str] = {}
        self._active_launch_tokens: set[str] = set()
        self._startup_cancellations: dict[str, Event] = {}
        self._browser_opened_tokens: set[str] = set()
        self._user_stopped_ids: set[str] = set()
        self._active_startups = 0
        self._parallel_startup_limit = max(1, config.launcher.maximum_parallel_startups)
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max(self.thread_pool.maxThreadCount(), self._parallel_startup_limit))
        self.setWindowTitle(config.platform_name)
        self.resize(config.window.width, config.window.height)
        self.setMinimumSize(config.window.minimum_width, config.window.minimum_height)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self.liveness_timer = QTimer(self)
        self.liveness_timer.setInterval(2000)
        self.liveness_timer.timeout.connect(self._sync_process_liveness)
        self.liveness_timer.start()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(82)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 14, 24, 14)
        header_layout.setSpacing(8)
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title = QLabel(self.config.platform_name)
        title.setObjectName("platformTitle")
        self.results_label = QLabel(self._application_count_text(len(self.apps)))
        self.results_label.setObjectName("platformSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(self.results_label)
        self.startup_summary = QLabel("")
        self.startup_summary.setObjectName("summary")
        about = QPushButton("About")
        settings = QPushButton("Settings")
        about.setObjectName("ghost")
        settings.setObjectName("ghost")
        about.setFixedHeight(34)
        settings.setFixedHeight(34)
        about.setToolTip("About this launcher")
        settings.setToolTip("View launcher settings")
        settings.clicked.connect(lambda: SettingsDialog(self.config, self).exec())
        about.clicked.connect(lambda: show_about(self, self.config.platform_name))
        header_layout.addLayout(title_box)
        header_layout.addStretch(1)
        header_layout.addWidget(self.startup_summary, 0, Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(settings, 0, Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(about, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(header)

        toolbar_holder = QWidget()
        toolbar_holder.setObjectName("toolbar")
        toolbar_holder.setFixedHeight(64)
        toolbar = QHBoxLayout(toolbar_holder)
        toolbar.setContentsMargins(24, 12, 24, 12)
        toolbar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search applications")
        self.search.setMinimumWidth(240)
        self.search.setMaximumWidth(560)
        self.search.setFixedHeight(40)
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search applications")
        self.category = QComboBox()
        self.category.addItems(["All categories"] + sorted({app.category for app in self.apps}))
        self.category.setFixedSize(190, 40)
        self.category.setAccessibleName("Application category")
        self.open_all_button = QPushButton("Open All")
        self.stop_all_button = QPushButton("Stop All")
        self.open_all_button.setObjectName("primary")
        self.stop_all_button.setObjectName("danger")
        self.open_all_button.setFixedSize(96, 40)
        self.stop_all_button.setFixedSize(92, 40)
        self.open_all_button.setToolTip("Open all visible applications")
        self.stop_all_button.setToolTip("Stop all running applications")
        self.open_all_button.clicked.connect(self.open_all_apps)
        self.stop_all_button.clicked.connect(self.stop_all_apps)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.category)
        toolbar.addStretch(1)
        toolbar.addWidget(self.open_all_button)
        toolbar.addWidget(self.stop_all_button)
        layout.addWidget(toolbar_holder)

        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("grid")
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(24, 20, 24, 24)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.empty_state = QLabel("No applications match the current filters.")
        self.empty_state.setObjectName("emptyState")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setMinimumHeight(180)
        self.empty_state.hide()
        self.app_scroll = QScrollArea()
        self.app_scroll.setWidgetResizable(True)
        self.app_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.app_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.app_scroll.setWidget(self.grid_widget)
        layout.addWidget(self.app_scroll, 1)
        self.setCentralWidget(root)
        self.search.textChanged.connect(self.apply_filters)
        self.category.currentTextChanged.connect(self.apply_filters)
        self._populate_cards()
        self._update_startup_summary()

    def _populate_cards(self) -> None:
        for app in self.apps:
            card = AppCard(app)
            card.open_clicked.connect(self.open_app)
            card.stop_clicked.connect(self.stop_app)
            card.restart_clicked.connect(self.restart_app)
            card.log_clicked.connect(self.view_log)
            self.cards[app.id] = card
        self._relayout_cards(force=True)

    def apply_filters(self) -> None:
        query = self.search.text().strip().lower()
        category = self.category.currentText()
        visible_ids = []
        for app in self.apps:
            haystack = f"{app.name} {app.description} {app.category}".lower()
            visible = (not query or query in haystack) and (
                category == "All categories" or app.category == category
            )
            if visible:
                visible_ids.append(app.id)
        self._filtered_app_ids = visible_ids
        visible_count = len(visible_ids)
        self.results_label.setText(self._application_count_text(visible_count))
        self.open_all_button.setEnabled(visible_count > 0)
        self._relayout_cards(force=True)

    def _desired_column_count(self, width: int | None = None) -> int:
        width = width or self.width()
        if width >= 1540:
            return 3
        if width >= 820:
            return 2
        return 1

    def _relayout_cards(self, force: bool = False, width: int | None = None) -> None:
        if not hasattr(self, "app_scroll"):
            return
        columns = self._desired_column_count(width)
        if not force and columns == self._column_count:
            return
        self._column_count = columns
        for card in self.cards.values():
            self.grid.removeWidget(card)
            card.hide()
        self.grid.removeWidget(self.empty_state)
        for column in range(3):
            self.grid.setColumnStretch(column, int(column < columns))
        if not self._filtered_app_ids:
            self.grid.addWidget(self.empty_state, 0, 0, 1, columns)
            self.empty_state.show()
            return
        self.empty_state.hide()
        for index, app_id in enumerate(self._filtered_app_ids):
            card = self.cards[app_id]
            self.grid.addWidget(card, index // columns, index % columns)
            card.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout_cards(width=event.size().width())

    @staticmethod
    def _application_count_text(count: int) -> str:
        return f"{count} application" if count == 1 else f"{count} applications"

    def open_app(self, app_id: str) -> None:
        self._user_stopped_ids.discard(app_id)
        existing = self.process_manager.get(app_id)
        if existing and existing.url:
            verified_url = self._verified_open_url(app_id, existing)
            if verified_url:
                self._open_url(verified_url)
            return
        if app_id in self._queued_ids or app_id in self._starting_ids:
            return
        if self._active_startups >= self._parallel_startup_limit:
            self._startup_queue.append(app_id)
            self._queued_ids.add(app_id)
            self.cards[app_id].set_status(ApplicationStatus.STARTING, "Queued")
            return
        self._start_app_now(app_id)

    def _start_app_now(self, app_id: str) -> None:
        app = self._app_by_id(app_id)
        if app_id in self._starting_ids:
            return
        token = str(uuid4())
        cancellation = Event()
        self._launch_tokens[app_id] = token
        self._active_launch_tokens.add(token)
        self._startup_cancellations[token] = cancellation
        self._active_startups += 1
        self._starting_ids.add(app_id)
        self._update_startup_summary()
        self.cards[app_id].set_status(ApplicationStatus.STARTING, "Checking environment")

        def work(progress):
            env = self.environment_manager.ensure_environment(app, progress=progress)
            if cancellation.is_set():
                return None
            progress("Starting application")
            state = self.process_manager.start(app, env)
            if cancellation.is_set():
                self.process_manager.stop(app.id)
            return state

        worker = Worker(work)
        worker.signals.progress.connect(lambda message: self._start_progress(app_id, token, message))
        worker.signals.finished.connect(lambda state: self._start_finished(app_id, token, state))
        worker.signals.failed.connect(lambda message, details: self._start_failed(app_id, token, message, details))
        self.thread_pool.start(worker)

    def _start_progress(self, app_id: str, token: str, message: str) -> None:
        if self._launch_tokens.get(app_id) != token:
            return
        self.cards[app_id].set_status(ApplicationStatus.STARTING, message)

    def _finish_startup_accounting(self, app_id: str, token: str) -> None:
        if token in self._active_launch_tokens:
            self._active_launch_tokens.discard(token)
            self._active_startups = max(0, self._active_startups - 1)
        self._startup_cancellations.pop(token, None)
        if self._launch_tokens.get(app_id) == token:
            self._starting_ids.discard(app_id)
        self._update_startup_summary()

    def _start_finished(self, app_id: str, token: str, state) -> None:
        if self._launch_tokens.get(app_id) != token:
            self._finish_startup_accounting(app_id, token)
            return
        self._finish_startup_accounting(app_id, token)
        if app_id in self._user_stopped_ids:
            # User pressed Stop while the app was still starting.
            self._user_stopped_ids.discard(app_id)
            self.process_manager.stop(app_id)
            self.cards[app_id].set_status(ApplicationStatus.STOPPED)
            self._start_next_queued_app()
            return
        tracked = self.process_manager.get(app_id)
        if not tracked:
            # The app is no longer tracked (stopped or crashed meanwhile).
            self.cards[app_id].set_status(ApplicationStatus.STOPPED)
            self._start_next_queued_app()
            return
        verified_url = self._verified_open_url(app_id, tracked)
        if (
            self.config.launcher.open_browser_after_start
            and verified_url
            and token not in self._browser_opened_tokens
        ):
            self.cards[app_id].set_status(ApplicationStatus.STARTING, "Opening browser")
            self._open_url(verified_url)
            self._browser_opened_tokens.add(token)
        self.cards[app_id].set_status(ApplicationStatus.RUNNING)
        self._start_next_queued_app()

    def _start_failed(self, app_id: str, token: str, message: str, details: str) -> None:
        if self._launch_tokens.get(app_id) != token:
            self._finish_startup_accounting(app_id, token)
            return
        if app_id in self._user_stopped_ids:
            # Expected failure: the user cancelled a starting app.
            self._user_stopped_ids.discard(app_id)
            self._finish_startup_accounting(app_id, token)
            self.cards[app_id].set_status(ApplicationStatus.STOPPED)
            self._start_next_queued_app()
            return
        self._finish_startup_accounting(app_id, token)
        LOG.error("Application failed to start: %s\n%s", message, details)
        self.cards[app_id].set_status(ApplicationStatus.FAILED)
        QMessageBox.warning(
            self,
            "Application could not start",
            f"{self._app_by_id(app_id).name} could not start.\n\n{message}\n\nOpen the application log for technical details.",
        )
        self._start_next_queued_app()

    def _start_next_queued_app(self) -> None:
        while self._startup_queue and self._active_startups < self._parallel_startup_limit:
            next_app_id = self._startup_queue.popleft()
            self._queued_ids.discard(next_app_id)
            if self.process_manager.get(next_app_id):
                continue
            self._start_app_now(next_app_id)
            break

    def stop_app(self, app_id: str) -> None:
        if app_id in self._queued_ids:
            self._queued_ids.discard(app_id)
            self._startup_queue = deque(item for item in self._startup_queue if item != app_id)
            self.cards[app_id].set_status(ApplicationStatus.STOPPED)
            self._update_startup_summary()
            return
        if app_id in self._starting_ids:
            # The startup worker is still running; remember the user's intent
            # so its eventual success/failure is treated as a clean stop.
            self._user_stopped_ids.add(app_id)
        token = self._launch_tokens.get(app_id)
        if token:
            cancellation = self._startup_cancellations.get(token)
            if cancellation:
                cancellation.set()
            self._browser_opened_tokens.discard(token)
        self.process_manager.stop(app_id)
        self.cards[app_id].set_status(ApplicationStatus.STOPPED)

    def open_all_apps(self) -> None:
        """Start every visible application."""

        for app in self.apps:
            card = self.cards[app.id]
            if card.isVisible():
                self.open_app(app.id)

    def stop_all_apps(self) -> None:
        """Stop every application and clear queued launches."""

        self._startup_queue.clear()
        self._queued_ids.clear()
        for cancellation in self._startup_cancellations.values():
            cancellation.set()
        self._starting_ids.clear()
        self._launch_tokens.clear()
        self._active_launch_tokens.clear()
        self._browser_opened_tokens.clear()
        self._user_stopped_ids.clear()
        self.process_manager.stop_all()
        self._active_startups = 0
        self._update_startup_summary()
        for card in self.cards.values():
            card.set_status(ApplicationStatus.STOPPED)

    def restart_app(self, app_id: str) -> None:
        self.stop_app(app_id)
        self.open_app(app_id)

    def view_log(self, app_id: str) -> None:
        state = self.process_manager.get(app_id)
        log_path = state.log_path if state else self.process_manager.logs_dir / f"{app_id}.log"
        LogDialog(log_path, self).exec()

    def _app_by_id(self, app_id: str) -> ApplicationManifest:
        for app in self.apps:
            if app.id == app_id:
                return app
        raise KeyError(app_id)

    def _open_url(self, url: str) -> None:
        """Open a local app URL without loading the user's browser extensions."""

        if os.name == "nt":
            if open_isolated_browser(url):
                return
            QMessageBox.warning(
                self,
                "Secure browser unavailable",
                "Microsoft Edge could not be opened in an isolated Guest window.",
            )
            return
        opened = QDesktopServices.openUrl(QUrl(url))
        if not opened:
            LOG.error("Desktop browser could not open local URL")

    def _verified_open_url(self, app_id: str, state) -> str | None:
        """Return a cache-busted URL only when it matches the live tracked process."""

        if not state or not state.url or not state.process or state.process.poll() is not None:
            return None
        if HealthChecker._port_from_url(state.url) != state.port:
            return None
        token = self._launch_tokens.get(app_id)
        if not token:
            return state.url
        parsed = urlparse(state.url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["launch_id"] = token
        return urlunparse(parsed._replace(query=urlencode(query)))

    def _update_startup_summary(self) -> None:
        """Show current parallel startup activity."""

        running = sum(
            1 for state in self.process_manager.running_states() if state.status == ApplicationStatus.RUNNING
        )
        queued = len(self._startup_queue)
        parts = [f"{running} running"]
        if self._active_startups:
            parts.append(f"{self._active_startups} starting")
        if queued:
            parts.append(f"{queued} queued")
        self.startup_summary.setText(" | ".join(parts))
        summary_state = "busy" if self._active_startups or queued else "active" if running else "idle"
        self.startup_summary.setProperty("state", summary_state)
        self.startup_summary.style().unpolish(self.startup_summary)
        self.startup_summary.style().polish(self.startup_summary)
        self.stop_all_button.setEnabled(bool(running or self._active_startups or queued))

    def _sync_process_liveness(self) -> None:
        """Mark cards Failed when a running app process has died."""

        for state in self.process_manager.running_states():
            if state.status != ApplicationStatus.RUNNING:
                continue
            if state.process and state.process.poll() is not None:
                self.process_manager.get(state.app_id)  # untracks the dead process
                token = self._launch_tokens.get(state.app_id)
                if token:
                    self._browser_opened_tokens.discard(token)
                if state.app_id in self.cards:
                    self.cards[state.app_id].set_status(ApplicationStatus.FAILED)
                LOG.warning("Application process exited unexpectedly: %s", state.app_id)
        self._update_startup_summary()

    def closeEvent(self, event) -> None:
        has_active_apps = bool(self.process_manager.running_states() or self._starting_ids or self._queued_ids)
        if self.config.launcher.stop_apps_on_exit and has_active_apps:
            response = QMessageBox.question(self, "Close launcher", "Stop running applications and close the launcher?")
            if response != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.stop_all_apps()
        super().closeEvent(event)
