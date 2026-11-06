"""Settings dialog."""

from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import QSettings, QThreadPool
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QListWidget, QStackedWidget, QSplitter, QWidget
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout,
)

from ..app_discovery import discover_apps
from ..app_registry import add_application
from ..dependency_manager import install_named_package, preview_runtime_dependencies, update_runtime_dependencies
from ..exceptions import LauncherError
from ..models import PlatformConfig
from .workers import Worker
from .styles import APP_STYLE, LIGHT_STYLE, HIGH_CONTRAST_STYLE


class SettingsDialog(QDialog):
    """Read-only settings summary."""

    def __init__(self, config: PlatformConfig, parent=None, on_saved=None) -> None:
        super().__init__(parent)
        self.config = config
        self.on_saved = on_saved
        self.thread_pool = QThreadPool(self)
        self.setWindowTitle("Settings")
        layout = QVBoxLayout(self)
        navigation = QListWidget()
        navigation.setAccessibleName("Settings sections")
        navigation.setFixedWidth(170)
        stack = QStackedWidget()
        self._settings_stack = stack
        for title in ("Appearance", "Add application", "Package manager", "Runtime health", "Network drive", "Security", "Diagnostics"):
            navigation.addItem(title)
        navigation.currentRowChanged.connect(stack.setCurrentIndex)
        splitter = QSplitter()
        splitter.addWidget(navigation)
        splitter.addWidget(stack)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        appearance = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance)
        self.theme = QComboBox(); self.theme.addItems(["Dark", "Light", "High contrast"])
        self.theme.setAccessibleName("Color theme")
        saved_theme = QSettings("UnifiedPipelineLauncher", "Launcher").value("theme", "Light")
        self.theme.setCurrentText(str(saved_theme))
        self.theme.currentTextChanged.connect(self._apply_theme)
        appearance_form.addRow("Theme", self.theme)
        appearance_page = QWidget(); appearance_layout = QVBoxLayout(appearance_page)
        appearance_layout.addWidget(appearance); appearance_layout.addStretch(1)
        stack.addWidget(appearance_page)

        group = QGroupBox("Add application")
        form = QFormLayout(group)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Application name")
        self.path = QLineEdit()
        self.path.setPlaceholderText("Path to a Streamlit .py file")
        path_button = QPushButton("Browse…")
        path_button.clicked.connect(self._browse_python)
        path_row = QVBoxLayout(); path_row.addWidget(self.path); path_row.addWidget(path_button)
        self.icon = QLineEdit()
        icon_button = QPushButton("Browse…")
        icon_button.clicked.connect(self._browse_icon)
        icon_row = QVBoxLayout(); icon_row.addWidget(self.icon); icon_row.addWidget(icon_button)
        self.error = QLabel(); self.error.setObjectName("emptyState")
        form.addRow("Application name *", self.name)
        form.addRow("Python script *", path_row)
        form.addRow("Icon", icon_row)

        advanced = QToolButton(); advanced.setText("Advanced settings"); advanced.setCheckable(True); advanced.setChecked(False)
        advanced_box = QGroupBox(); advanced_box.setVisible(False)
        advanced.toggled.connect(advanced_box.setVisible)
        advanced_form = QFormLayout(advanced_box)
        self.description = QLineEdit(); self.category = QLineEdit(); self.version = QLineEdit("1.0.0")
        self.category.setText("General")
        advanced_form.addRow("Description", self.description)
        advanced_form.addRow("Category", self.category)
        advanced_form.addRow("Version", self.version)
        self.add_button = QPushButton("Add application")
        self.add_button.clicked.connect(self._save)
        self.update_button = QPushButton("Scan and update Python packages")
        self.update_button.clicked.connect(self._update_packages)
        self.preview_button = QPushButton("Preview package changes")
        self.preview_button.clicked.connect(self._preview_packages)
        self.manual_package = QLineEdit()
        self.manual_package.setPlaceholderText("e.g. scikit-learn or pandas>=2.0")
        self.manual_button = QPushButton("Install named package")
        self.manual_button.clicked.connect(self._install_named_package)
        self.package_status = QLabel()
        self.package_summary = QLabel("Package health: not checked")
        self.package_summary.setObjectName("emptyState")
        self.package_table = QTableWidget(0, 3)
        self.package_table.setHorizontalHeaderLabels(("Library", "Status", "Details"))
        self.package_table.setMinimumHeight(130)
        self.package_table.horizontalHeader().setStretchLastSection(True)
        manual_row = QVBoxLayout(); manual_row.addWidget(self.manual_package); manual_row.addWidget(self.manual_button)
        add_page = QWidget(); add_layout = QVBoxLayout(add_page)
        add_layout.addWidget(group); add_layout.addWidget(advanced); add_layout.addWidget(advanced_box); add_layout.addWidget(self.error); add_layout.addWidget(self.add_button); add_layout.addStretch(1)
        stack.addWidget(add_page)
        package_page = QWidget(); package_layout = QVBoxLayout(package_page)
        package_layout.addWidget(self.preview_button); package_layout.addWidget(self.update_button); package_layout.addLayout(manual_row); package_layout.addWidget(self.package_summary); package_layout.addWidget(self.package_status); package_layout.addWidget(self.package_table); stack.addWidget(package_page)
        runtime_page = QWidget(); runtime_layout = QVBoxLayout(runtime_page)
        runtime_layout.addWidget(QLabel(f"Local cache\n{config.paths.local_cache_directory}")); runtime_layout.addWidget(QLabel(f"Runtime\n{config.paths.runtime_python}")); runtime_layout.addStretch(1); stack.addWidget(runtime_page)
        network_page = QWidget(); network_layout = QVBoxLayout(network_page)
        network_layout.addWidget(QLabel(f"Application source\n{config.paths.apps_directory}")); network_layout.addWidget(QLabel("Streamlit binding: 127.0.0.1 only")); network_layout.addStretch(1); stack.addWidget(network_page)
        for title, text in (("Security", "Loopback-only application sessions and isolated browser profiles."), ("Diagnostics", "Use the debug launcher and local logs for repair details.")):
            page = QWidget(); page_layout = QVBoxLayout(page); page_layout.addWidget(QLabel(text)); page_layout.addStretch(1); stack.addWidget(page)
        navigation.setCurrentRow(0)

    def _apply_theme(self, theme: str) -> None:
        QSettings("UnifiedPipelineLauncher", "Launcher").setValue("theme", theme)
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet({"Light": LIGHT_STYLE, "High contrast": HIGH_CONTRAST_STYLE}.get(theme, APP_STYLE))
            for widget in application.topLevelWidgets():
                widget.style().unpolish(widget); widget.style().polish(widget); widget.update()

    def _install_named_package(self) -> None:
        requirement = self.manual_package.text().strip()
        self.manual_button.setEnabled(False)
        self.package_status.setText(f"Installing {requirement}…")

        def work(progress):
            return install_named_package(
                self.config.paths.runtime_python,
                self.config.paths.local_cache_directory / "packages",
                requirement,
                progress=progress,
            )

        worker = Worker(work)
        worker.signals.progress.connect(self._package_progress)
        worker.signals.finished.connect(self._manual_package_finished)
        worker.signals.failed.connect(lambda message, details: self._manual_package_failed(message))
        self.thread_pool.start(worker)

    def _manual_package_finished(self, result: dict) -> None:
        self.manual_button.setEnabled(True)
        self._set_package_status(result["package"], "✓ Installed" if result["status"] == "installed" else "✕ Failed", result["details"])
        self.package_status.setText(result["details"])

    def _manual_package_failed(self, message: str) -> None:
        self.manual_button.setEnabled(True)
        self.package_status.setText(f"Package install failed: {message}")

    def _update_packages(self) -> None:
        self.update_button.setEnabled(False)
        self.package_status.setText("Scanning applications…")
        self.package_summary.setText("Package health: scanning…")
        self.package_table.setRowCount(0)

        def work(progress):
            return update_runtime_dependencies(
                self.config.paths.apps_directory,
                self.config.paths.runtime_python,
                self.config.paths.local_cache_directory / "packages",
                progress=progress,
            )

        worker = Worker(work)
        worker.signals.progress.connect(self._package_progress)
        worker.signals.finished.connect(self._packages_updated)
        worker.signals.failed.connect(lambda message, details: self._packages_failed(message))
        self.thread_pool.start(worker)

    def _preview_packages(self) -> None:
        self.preview_button.setEnabled(False)
        self.package_status.setText("Preparing package preview…")
        def work(progress):
            return preview_runtime_dependencies(self.config.paths.apps_directory, self.config.paths.runtime_python)
        worker = Worker(work)
        worker.signals.finished.connect(self._packages_previewed)
        worker.signals.failed.connect(lambda message, details: self._preview_failed(message))
        self.thread_pool.start(worker)

    def _packages_previewed(self, result: dict) -> None:
        self.preview_button.setEnabled(True)
        self.package_table.setRowCount(0)
        for package in result["installed"]:
            self._set_package_row(package, "✓ Installed", "No change")
        for package in result["missing"]:
            self._set_package_row(package, "＋ Install", "Will be installed")
        self.package_summary.setText(f"Preview: {len(result['missing'])} to install, {len(result['installed'])} already available")
        self.package_status.setText("Preview complete; no packages were changed.")

    def _preview_failed(self, message: str) -> None:
        self.preview_button.setEnabled(True)
        self.package_status.setText(f"Package preview failed: {message}")

    def _packages_updated(self, result: dict) -> None:
        self.update_button.setEnabled(True)
        self.package_table.setRowCount(0)
        for package in result["skipped"]:
            self._set_package_row(package, "✓ Installed", "Already available")
        for package in result["installed"]:
            self._set_package_row(package, "✓ Installed", "Installed successfully")
        for package, error in zip(result["failed"], result["errors"]):
            self._set_package_row(package, "✕ Failed", error)
        self.package_status.setText(
            f"Package update complete: {len(result['installed'])} installed, "
            f"{len(result['skipped'])} already available, {len(result['failed'])} failed."
        )
        self.package_summary.setText(f"Package health: {len(result['skipped']) + len(result['installed'])} installed, {len(result['failed'])} failed, {len(result['missing'])} discovered missing")

    def _packages_failed(self, message: str) -> None:
        self.update_button.setEnabled(True)
        self.package_status.setText(f"Package update failed: {message}")

    def _set_package_row(self, package: str, status: str, details: str) -> None:
        row = self.package_table.rowCount()
        self.package_table.insertRow(row)
        self.package_table.setItem(row, 0, QTableWidgetItem(package))
        self.package_table.setItem(row, 1, QTableWidgetItem(status))
        self.package_table.setItem(row, 2, QTableWidgetItem(details))

    def _package_progress(self, message: str) -> None:
        parts = message.split("|", 2)
        if len(parts) == 2 and parts[0] == "installing":
            self._set_package_row(parts[1], "… Installing", "pip is resolving and installing")
        elif len(parts) == 2 and parts[0] == "installed":
            self._set_package_status(parts[1], "✓ Installed", "Installed successfully")
        elif len(parts) == 3 and parts[0] == "failed":
            self._set_package_status(parts[1], "✕ Failed", parts[2])
        else:
            self.package_status.setText(message)

    def _set_package_status(self, package: str, status: str, details: str) -> None:
        for row in range(self.package_table.rowCount()):
            if self.package_table.item(row, 0).text() == package:
                self.package_table.item(row, 1).setText(status)
                self.package_table.item(row, 2).setText(details)
                return
        self._set_package_row(package, status, details)

    def _browse_python(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Streamlit application", "", "Python files (*.py)")
        if path:
            self.path.setText(path)

    def _browse_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select application icon", "", "Images (*.svg *.png *.ico)")
        if path:
            self.icon.setText(path)

    def _save(self) -> None:
        name = self.name.text().strip()
        raw_path = self.path.text().strip()
        script = Path(raw_path).expanduser() if raw_path else Path()
        if not name or not raw_path:
            self.error.setText("Application name and Python script path are required.")
            return
        if script.suffix.lower() != ".py" or not script.is_file():
            self.error.setText("Select an existing Python (.py) file.")
            return
        icon = self.icon.text().strip()
        if icon and not Path(icon).expanduser().is_file():
            self.error.setText("The selected icon file does not exist.")
            return
        try:
            existing = discover_apps(self.config.paths.apps_directory, include_disabled=True)
            normalized = str(script.resolve()).casefold()
            if any(str(app.entrypoint.resolve()).casefold() == normalized for app in existing):
                self.error.setText("This Python script is already registered.")
                return
            used_ids = {app.id for app in existing}
            base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app"
            app_id = base; index = 2
            while app_id in used_ids:
                app_id = f"{base}-{index}"; index += 1
            entry = {
                "id": app_id, "path": str(script.resolve()), "name": name,
                "version": self.version.text().strip() or "1.0.0",
                "description": self.description.text().strip(),
                "category": self.category.text().strip() or "General",
                "display_order": max((app.display_order for app in existing), default=0) + 1,
                "enabled": True, "archived": False,
            }
            if icon:
                entry["icon_path"] = str(Path(icon).expanduser().resolve())
            self.add_button.setEnabled(False)
            add_application(self.config.paths.apps_directory / "apps.json", entry)
        except LauncherError as exc:
            self.error.setText(str(exc))
            return
        finally:
            self.add_button.setEnabled(True)
        self.error.setText("Application added.")
        if self.on_saved:
            self.on_saved(app_id)
