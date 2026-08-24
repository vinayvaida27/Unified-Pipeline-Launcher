from __future__ import annotations

import os
import threading
import time
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from launcher.app_discovery import discover_apps
from launcher.models import ApplicationRuntimeState, ApplicationStatus
from launcher.ui.main_window import MainWindow


class FakeProcess:
    def __init__(self, pid=1234):
        self.pid = pid
        self.terminated = False

    def poll(self):
        return None if not self.terminated else 0


class FakeEnvironmentManager:
    pass


class BlockingEnvironmentManager:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()

    def ensure_environment(self, app, progress):
        self.entered.set()
        assert self.release.wait(timeout=5)
        return object()


class CountingBlockingEnvironmentManager:
    def __init__(self, expected: int):
        self.expected = expected
        self.entered = 0
        self.lock = threading.Lock()
        self.all_entered = threading.Event()
        self.release = threading.Event()

    def ensure_environment(self, app, progress):
        with self.lock:
            self.entered += 1
            if self.entered == self.expected:
                self.all_entered.set()
        assert self.release.wait(timeout=5)
        return object()


class FakeProcessManager:
    def __init__(self, state=None):
        self.state = state
        self.logs_dir = None
        self.stop_calls = []

    def get(self, app_id):
        return self.state if self.state and self.state.app_id == app_id and self.state.process.poll() is None else None

    def stop(self, app_id):
        self.stop_calls.append(app_id)
        if self.state and self.state.app_id == app_id:
            self.state.process.terminated = True
            self.state = None

    def stop_all(self):
        if self.state:
            self.stop(self.state.app_id)

    def running_states(self):
        return [self.state] if self.state else []

    def mark_running_from_url(self, app_id, url):
        state = self.get(app_id)
        if not state or state.port != int(url.rsplit(":", 1)[1]):
            return None
        state.url = url
        state.status = ApplicationStatus.RUNNING
        return state


class RecordingProcessManager(FakeProcessManager):
    def __init__(self):
        super().__init__()
        self.start_calls = []

    def start(self, app, environment):
        self.start_calls.append((app, environment))
        return None


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    return app


def _app(repo_root):
    return discover_apps(repo_root / "src" / "apps")[0]


def _state(app, tmp_path, port=63260, pid=1234):
    return ApplicationRuntimeState(
        app_id=app.id,
        app_name=app.name,
        app_version=app.version,
        process=FakeProcess(pid=pid),
        process_id=pid,
        port=port,
        url=f"http://127.0.0.1:{port}",
        start_time=datetime.now(timezone.utc).isoformat(),
        log_path=tmp_path / f"{app.id}.log",
        status=ApplicationStatus.RUNNING,
        environment_path=tmp_path / "env",
        entrypoint_path=app.entrypoint,
    )


def _window(qt_app, config, app, process_manager):
    window = MainWindow(config, [app], FakeEnvironmentManager(), process_manager)
    window.liveness_timer.stop()
    return window


def test_startup_jobs_use_a_dedicated_bounded_thread_pool(qt_app, config, repo_root):
    app = _app(repo_root)
    config = replace(config, launcher=replace(config.launcher, maximum_parallel_startups=4))
    window = _window(qt_app, config, app, FakeProcessManager())

    assert window.thread_pool is not QThreadPool.globalInstance()
    assert window.thread_pool.parent() is window
    assert window.thread_pool.maxThreadCount() == 4


def test_liveness_timer_finishes_a_delayed_startup_signal(qt_app, config, repo_root, tmp_path):
    app = _app(repo_root)
    state = _state(app, tmp_path)
    config = replace(config, launcher=replace(config.launcher, open_browser_after_start=False))
    window = _window(qt_app, config, app, FakeProcessManager(state))
    token = "delayed-finish"
    window._launch_tokens[app.id] = token
    window._active_launch_tokens.add(token)
    window._starting_ids.add(app.id)
    window._active_startups = 1
    window.cards[app.id].set_status(ApplicationStatus.STARTING, "Starting application")

    thread_pool = window.thread_pool
    window.thread_pool = SimpleNamespace(activeThreadCount=lambda: 1)
    window._sync_process_liveness()
    assert window._active_startups == 1

    window.thread_pool = thread_pool
    window._sync_process_liveness()
    assert window._active_startups == 0
    assert app.id not in window._starting_ids
    assert window.cards[app.id].status.text() == ApplicationStatus.RUNNING.value


def test_only_one_browser_open_occurs_per_launch(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    state = _state(app, tmp_path)
    process_manager = FakeProcessManager(state)
    window = _window(qt_app, config, app, process_manager)
    opened = []
    monkeypatch.setattr(window, "_open_url", opened.append)
    token = "launch-1"
    window._launch_tokens[app.id] = token

    window._start_finished(app.id, token, state)
    window._start_finished(app.id, token, state)

    assert len(opened) == 1
    assert opened[0] == f"http://127.0.0.1:{state.port}?launch_id={token}"


def test_stale_worker_completion_is_ignored(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    state = _state(app, tmp_path)
    window = _window(qt_app, config, app, FakeProcessManager(state))
    opened = []
    monkeypatch.setattr(window, "_open_url", opened.append)
    window._launch_tokens[app.id] = "current-launch"
    window._active_launch_tokens.add("stale-launch")
    window._active_startups = 1

    window._start_finished(app.id, "stale-launch", state)

    assert opened == []
    assert window._active_startups == 0
    assert window._launch_tokens[app.id] == "current-launch"


def test_open_running_app_does_not_restart(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    state = _state(app, tmp_path)
    window = _window(qt_app, config, app, FakeProcessManager(state))
    opened = []
    monkeypatch.setattr(window, "_open_url", opened.append)
    monkeypatch.setattr(window, "_start_app_now", lambda app_id: pytest.fail("running app should not restart"))

    window.open_app(app.id)

    assert opened == [f"http://127.0.0.1:{state.port}"]


def test_open_running_app_ignores_malformed_url(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    state = _state(app, tmp_path)
    state.url = "http://127.0.0.1:bad"
    window = _window(qt_app, config, app, FakeProcessManager(state))
    opened = []
    starts = []
    monkeypatch.setattr(window, "_open_url", opened.append)
    monkeypatch.setattr(window, "_start_app_now", starts.append)

    window.open_app(app.id)

    assert opened == []
    assert starts == []


def test_windows_browser_does_not_fall_back_to_extension_enabled_profile(
    qt_app, config, repo_root, monkeypatch
):
    app = _app(repo_root)
    window = _window(qt_app, config, app, FakeProcessManager())
    warnings = []
    monkeypatch.setattr("launcher.ui.main_window.open_isolated_browser", lambda url: False)
    monkeypatch.setattr(
        "launcher.ui.main_window.QDesktopServices.openUrl",
        lambda url: pytest.fail("default browser profile must not receive app data"),
    )
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: warnings.append(args)))

    window._open_url("http://127.0.0.1:61234")

    assert len(warnings) == 1


def test_launcher_layout_fits_at_minimum_width(qt_app, config, repo_root):
    base_app = _app(repo_root)
    apps = [
        replace(
            base_app,
            id=f"layout-{index}",
            name=f"Long Operational Application Name {index}",
            display_order=index,
        )
        for index in range(1, 5)
    ]
    window = MainWindow(config, apps, FakeEnvironmentManager(), FakeProcessManager())
    window.liveness_timer.stop()
    window.resize(config.window.minimum_width, config.window.minimum_height)
    window.show()
    qt_app.processEvents()

    assert window.app_scroll.horizontalScrollBar().maximum() == 0
    assert window._column_count == 2
    window.close()


def test_launcher_uses_three_columns_on_wide_screens(qt_app, config, repo_root):
    base_app = _app(repo_root)
    apps = [
        replace(base_app, id=f"wide-{index}", name=f"Application {index}", display_order=index)
        for index in range(1, 5)
    ]
    window = MainWindow(config, apps, FakeEnvironmentManager(), FakeProcessManager())
    window.liveness_timer.stop()
    window.resize(1800, 900)
    window.show()
    qt_app.processEvents()

    positions = []
    for app in apps:
        item_index = window.grid.indexOf(window.cards[app.id])
        row, column, _, _ = window.grid.getItemPosition(item_index)
        positions.append((row, column))

    assert window._column_count == 3
    assert positions == [(0, 0), (0, 1), (0, 2), (1, 0)]
    window.close()


def test_filter_shows_result_count_and_empty_state(qt_app, config, repo_root):
    app = _app(repo_root)
    window = _window(qt_app, config, app, FakeProcessManager())
    window.show()

    window.search.setText("not-an-application")
    qt_app.processEvents()

    assert window.results_label.text() == "0 applications"
    assert window.empty_state.isVisible()
    window.close()


def test_filter_compacts_matching_cards_to_first_grid_cell(qt_app, config, repo_root):
    base_app = _app(repo_root)
    apps = [
        replace(base_app, id=f"filter-{index}", name=name, display_order=index)
        for index, name in enumerate(("Alpha", "Beta", "Gamma", "Target Application"), start=1)
    ]
    window = MainWindow(config, apps, FakeEnvironmentManager(), FakeProcessManager())
    window.liveness_timer.stop()
    window.resize(1800, 900)
    window.show()

    window.search.setText("Target")
    qt_app.processEvents()

    item_index = window.grid.indexOf(window.cards["filter-4"])
    row, column, _, _ = window.grid.getItemPosition(item_index)
    assert (row, column) == (0, 0)
    window.close()


def test_card_hides_actions_that_are_not_available(qt_app, config, repo_root):
    app = _app(repo_root)
    window = _window(qt_app, config, app, FakeProcessManager())
    card = window.cards[app.id]

    card.set_status(ApplicationStatus.STOPPED)
    assert card.stop_button.isHidden()
    assert card.restart_button.isHidden()

    card.set_status(ApplicationStatus.STARTING)
    assert not card.stop_button.isHidden()
    assert card.restart_button.isHidden()

    card.set_status(ApplicationStatus.RUNNING)
    assert not card.stop_button.isHidden()
    assert not card.restart_button.isHidden()
    window.close()


def test_duplicate_start_worker_is_prevented(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    window = _window(qt_app, config, app, FakeProcessManager())
    starts = []
    monkeypatch.setattr(window, "_start_app_now", starts.append)

    window._starting_ids.add(app.id)
    window.open_app(app.id)

    assert starts == []


def test_stop_all_cancels_an_inflight_environment_start(qt_app, config, repo_root):
    app = _app(repo_root)
    environment_manager = BlockingEnvironmentManager()
    process_manager = RecordingProcessManager()
    window = MainWindow(config, [app], environment_manager, process_manager)
    window.liveness_timer.stop()

    window.open_app(app.id)
    assert environment_manager.entered.wait(timeout=5)
    window.stop_all_apps()
    environment_manager.release.set()

    deadline = time.monotonic() + 5
    while window._active_startups and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.01)

    assert window._active_startups == 0
    assert process_manager.start_calls == []


def test_close_cancels_an_inflight_environment_start(qt_app, config, repo_root, monkeypatch):
    app = _app(repo_root)
    environment_manager = BlockingEnvironmentManager()
    process_manager = RecordingProcessManager()
    window = MainWindow(config, [app], environment_manager, process_manager)
    window.liveness_timer.stop()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )

    window.open_app(app.id)
    assert environment_manager.entered.wait(timeout=5)
    window.close()
    environment_manager.release.set()

    deadline = time.monotonic() + 5
    while window._active_startups and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.01)

    assert window._active_startups == 0
    assert process_manager.start_calls == []


def test_stop_all_cancels_ten_apps_across_active_and_queued_starts(qt_app, config, repo_root):
    base_app = _app(repo_root)
    apps = [
        replace(base_app, id=f"queued-{index}", name=f"Queued {index}", display_order=index + 1)
        for index in range(10)
    ]
    config = replace(config, launcher=replace(config.launcher, maximum_parallel_startups=3))
    environment_manager = CountingBlockingEnvironmentManager(expected=3)
    process_manager = RecordingProcessManager()
    window = MainWindow(config, apps, environment_manager, process_manager)
    window.liveness_timer.stop()
    window.show()
    qt_app.processEvents()

    window.open_all_apps()
    assert environment_manager.all_entered.wait(timeout=5)
    assert window._active_startups == 3
    assert len(window._startup_queue) == 7

    window.stop_all_apps()
    environment_manager.release.set()
    deadline = time.monotonic() + 5
    while window._active_startups and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.01)

    assert process_manager.start_calls == []
    assert not window._startup_queue
    assert all(card.status.text() == ApplicationStatus.STOPPED.value for card in window.cards.values())
    window.close()


def test_close_stops_a_running_child(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    state = _state(app, tmp_path)
    process_manager = FakeProcessManager(state)
    window = _window(qt_app, config, app, process_manager)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )
    window.show()

    window.close()

    assert process_manager.stop_calls == [app.id]
    assert process_manager.get(app.id) is None
