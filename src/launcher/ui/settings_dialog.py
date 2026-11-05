"""Settings dialog."""

from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QMessageBox, QPushButton, QToolButton, QVBoxLayout,
)

from ..app_discovery import discover_apps
from ..app_registry import add_application
from ..exceptions import LauncherError
from ..models import PlatformConfig


class SettingsDialog(QDialog):
    """Read-only settings summary."""

    def __init__(self, config: PlatformConfig, parent=None, on_saved=None) -> None:
        super().__init__(parent)
        self.config = config
        self.on_saved = on_saved
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
        layout.addWidget(group); layout.addWidget(advanced); layout.addWidget(advanced_box); layout.addWidget(self.error); layout.addWidget(self.add_button)

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
