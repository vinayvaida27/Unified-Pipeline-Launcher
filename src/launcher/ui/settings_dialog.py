"""Settings dialog."""

from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout,
)

from ..app_discovery import discover_apps
from ..app_registry import add_application
from ..dependency_manager import install_named_package, update_runtime_dependencies
from ..exceptions import LauncherError
from ..models import PlatformConfig
from .workers import Worker


class SettingsDialog(QDialog):
    """Read-only settings summary."""

    def __init__(self, config: PlatformConfig, parent=None, on_saved=None) -> None:
        super().__init__(parent)
        self.config = config
        self.on_saved = on_saved
        self.thread_pool = QThreadPool(self)
        self.setWindowTitle("Settings")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Local cache: {config.paths.local_cache_directory}"))
        layout.addWidget(QLabel(f"Apps directory: {config.paths.apps_directory}"))
        layout.addWidget(QLabel(f"Runtime: {config.paths.runtime_python}"))

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
        self.manual_package = QLineEdit()
        self.manual_package.setPlaceholderText("e.g. scikit-learn or pandas>=2.0")
        self.manual_button = QPushButton("Install named package")
        self.manual_button.clicked.connect(self._install_named_package)
        self.package_status = QLabel()
        self.package_table = QTableWidget(0, 3)
        self.package_table.setHorizontalHeaderLabels(("Library", "Status", "Details"))
        self.package_table.setMinimumHeight(130)
        self.package_table.horizontalHeader().setStretchLastSection(True)
        manual_row = QVBoxLayout(); manual_row.addWidget(self.manual_package); manual_row.addWidget(self.manual_button)
        layout.addWidget(group); layout.addWidget(advanced); layout.addWidget(advanced_box); layout.addWidget(self.error); layout.addWidget(self.add_button); layout.addWidget(self.update_button); layout.addLayout(manual_row); layout.addWidget(self.package_status); layout.addWidget(self.package_table)

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
