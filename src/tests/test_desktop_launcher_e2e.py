from __future__ import annotations

import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from launcher.app_discovery import discover_apps
from launcher.environment_manager import EnvironmentManager
from launcher.models import ApplicationStatus
from launcher.process_manager import ProcessManager
from launcher.ui.main_window import MainWindow


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_open_button_launches_a_real_streamlit_child(qt_app, config, repo_root, tmp_path):
    behavior = replace(config.launcher, open_browser_after_start=False)
    config = replace(config, launcher=behavior)
    app = discover_apps(repo_root / "apps")[0]
    process_manager = ProcessManager(tmp_path / "logs")
    environment_manager = EnvironmentManager(config, Path(sys.executable))
    window = MainWindow(config, [app], environment_manager, process_manager)
    window.show()

    try:
        QTest.mouseClick(window.cards[app.id].open_button, Qt.MouseButton.LeftButton)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            qt_app.processEvents()
            state = process_manager.get(app.id)
            if (
                state
                and state.status == ApplicationStatus.RUNNING
                and app.id not in window._starting_ids
                and window._active_startups == 0
            ):
                break
            QTest.qWait(25)
        else:
            pytest.fail("launcher UI did not reach Running")

        assert window.cards[app.id].status.text() == ApplicationStatus.RUNNING.value
        assert process_manager.get(app.id).process.poll() is None

        screenshot = os.environ.get("LAUNCHER_AUDIT_SCREENSHOT")
        if screenshot:
            assert window.grab().save(screenshot)
    finally:
        process_manager.stop_all()
        window.close()
