from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from launcher.ui.settings_dialog import SettingsDialog


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_settings_has_left_navigation_and_theme_switch(qt_app, temp_config):
    settings = QSettings("UnifiedPipelineLauncher", "Launcher")
    settings.clear()
    dialog = SettingsDialog(temp_config)
    assert dialog._settings_stack.count() == 7
    assert dialog.theme.currentText() == "Light"
    dialog.theme.setCurrentText("Dark")
    assert settings.value("theme") == "Dark"
    assert "#0f1115" in QApplication.instance().styleSheet()
    dialog.theme.setCurrentText("Light")
    assert settings.value("theme") == "Light"
    dialog.close()
