from __future__ import annotations

import threading
import time

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from launcher import main as startup
from launcher.exceptions import LauncherError, RuntimeNotFoundError, RuntimeValidationError


def test_startup_work_keeps_qt_timer_responsive(config):
    qt_app = QApplication.instance() or QApplication([])
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(threading.get_ident()))
    timer.start(10)
    gui_thread = threading.get_ident()
    worker_threads = []

    def slow_copy(progress):
        worker_threads.append(threading.get_ident())
        progress("Copying synthetic files")
        time.sleep(0.2)
        return "ready"

    try:
        assert startup._run_with_progress(config, qt_app, "Preparing", slow_copy) == "ready"
    finally:
        timer.stop()
    assert len(ticks) >= 3, "The GUI event loop was blocked during startup work"
    assert all(thread == gui_thread for thread in ticks)
    assert worker_threads[0] != gui_thread


def test_startup_worker_failure_reaches_caller(config):
    qt_app = QApplication.instance() or QApplication([])

    def fail(progress):
        raise PermissionError("synthetic access denied")

    with pytest.raises(LauncherError, match="synthetic access denied"):
        startup._run_with_progress(config, qt_app, "Preparing", fail)


def test_runtime_not_found_survives_worker_for_download_fallback(config):
    qt_app = QApplication.instance() or QApplication([])

    def missing(progress):
        raise RuntimeNotFoundError("synthetic runtime missing")

    with pytest.raises(RuntimeNotFoundError, match="synthetic runtime missing"):
        startup._run_with_progress(config, qt_app, "Checking", missing)


@pytest.mark.parametrize("invalid", [True, False], ids=["invalid-runtime", "valid-runtime"])
def test_downloaded_runtime_is_validated_without_cache_sync(config, tmp_path, monkeypatch, invalid):
    qt_app = QApplication.instance() or QApplication([])
    downloaded = tmp_path / "downloaded runtime" / "python.exe"
    validated = []
    gui_thread = threading.get_ident()
    assert config.runtime.sync_to_local_cache is False
    monkeypatch.setattr(startup.RuntimeDownloader, "ensure_runtime", lambda self, progress: downloaded)

    def validate(self, python_path):
        validated.append((python_path, threading.get_ident()))
        if invalid:
            raise RuntimeValidationError("downloaded runtime is missing encodings")

    monkeypatch.setattr(startup.RuntimeResolver, "validate", validate)
    if invalid:
        with pytest.raises(RuntimeValidationError, match="missing encodings"):
            startup._download_runtime_with_dialog(config, qt_app)
    else:
        assert startup._download_runtime_with_dialog(config, qt_app) == downloaded
    assert len(validated) == 1
    assert validated[0][0] == downloaded
    assert validated[0][1] != gui_thread
