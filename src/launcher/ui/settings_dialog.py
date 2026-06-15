"""Settings dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from ..models import PlatformConfig


class SettingsDialog(QDialog):
    """Read-only settings summary."""

    def __init__(self, config: PlatformConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Local cache: {config.paths.local_cache_directory}"))
        layout.addWidget(QLabel(f"Apps directory: {config.paths.apps_directory}"))
        layout.addWidget(QLabel(f"Runtime: {config.paths.runtime_python}"))
