from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

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


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    return app


def _app(repo_root):
    return discover_apps(repo_root / "apps")[0]


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
    window.ready_log_timer.stop()
    window.liveness_timer.stop()
    return window


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


def test_sync_ready_logs_does_not_open_browser(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    state = _state(app, tmp_path)
    state.status = ApplicationStatus.STARTING
    state.url = None
    state.log_path.write_text(
        "You can now view your Streamlit app in your browser.\n"
        f"URL: http://127.0.0.1:{state.port}\n",
        encoding="utf-8",
    )
    process_manager = FakeProcessManager(state)
    window = _window(qt_app, config, app, process_manager)
    opened = []
    monkeypatch.setattr(window, "_open_url", opened.append)
    token = "launch-1"
    window._launch_tokens[app.id] = token
    window._starting_ids.add(app.id)
    window._active_launch_tokens.add(token)
    window._active_startups = 1

    window._sync_ready_logs()

    assert opened == []
    assert state.status == ApplicationStatus.RUNNING


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


def test_duplicate_start_worker_is_prevented(qt_app, config, repo_root, tmp_path, monkeypatch):
    app = _app(repo_root)
    window = _window(qt_app, config, app, FakeProcessManager())
    starts = []
    monkeypatch.setattr(window, "_start_app_now", starts.append)

    window._starting_ids.add(app.id)
    window.open_app(app.id)

    assert starts == []
