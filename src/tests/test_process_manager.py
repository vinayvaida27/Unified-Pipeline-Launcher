from __future__ import annotations

import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from launcher.app_discovery import discover_apps
from launcher.exceptions import ApplicationHealthCheckError, ApplicationStartError, ApplicationStopError
from launcher.models import EnvironmentState
from launcher.process_manager import ProcessManager


class FakeProcess:
    def __init__(self, pid=1234):
        self.pid = pid
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if not self.terminated else 0

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True
        self.terminated = True

    def wait(self, timeout=None):
        return 0


class FakeHealth:
    def wait_until_healthy(self, process, port, timeout_seconds, log_path=None):
        return f"http://127.0.0.1:{port}"


class StubbornFakeProcess(FakeProcess):
    def wait(self, timeout=None):
        if not self.killed:
            raise subprocess.TimeoutExpired("fixture", timeout)
        return 0


def _env(tmp_path: Path):
    return EnvironmentState("hello-pipeline", "1.0.0", tmp_path / "env", tmp_path / "env" / "Scripts" / "python.exe", True, tmp_path / "marker")


def test_builds_correct_command_list(repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    command = manager.build_command(app, _env(tmp_path), 5555)
    assert command[1:4] == ["-m", "streamlit", "run"]
    assert "--server.address" in command
    assert "127.0.0.1" in command
    assert "--server.port" in command
    assert "5555" in command
    assert command[command.index("--server.enableCORS") + 1] == "true"
    assert command[command.index("--server.enableXsrfProtection") + 1] == "true"


def test_stops_matching_stale_process_before_start(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    environment = _env(tmp_path)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    marker = tmp_path / f"{app.id}.runtime.json"
    executable = str(environment.python_path.resolve()).lower()
    stale_identity = {"created_at": 42, "executable": executable}
    marker.write_text(
        json.dumps({"pid": 9876, "identity": stale_identity, "entrypoint": str(app.entrypoint)}),
        encoding="utf-8",
    )
    terminated = []
    monkeypatch.setattr(
        manager,
        "_process_identity",
        lambda pid: stale_identity if pid == 9876 else {"created_at": 43, "executable": executable},
    )
    monkeypatch.setattr(manager, "_terminate_process_tree", lambda pid: terminated.append(pid) or True)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: FakeProcess())

    manager.start(app, environment)

    assert terminated == [9876]
    assert json.loads(marker.read_text(encoding="utf-8"))["pid"] == 1234


def test_refuses_to_kill_app_owned_by_live_launcher(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    marker = tmp_path / f"{app.id}.runtime.json"
    child_identity = {"created_at": 42, "executable": "python.exe"}
    owner_identity = {"created_at": 43, "executable": "launcher.exe"}
    marker.write_text(
        json.dumps(
            {
                "pid": 9876,
                "identity": child_identity,
                "owner_pid": 8765,
                "owner_identity": owner_identity,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        manager,
        "_process_identity",
        lambda pid: owner_identity if pid == 8765 else child_identity,
    )
    monkeypatch.setattr(
        manager,
        "_terminate_process_tree",
        lambda pid: pytest.fail("a live launcher's app must not be terminated"),
    )

    with pytest.raises(ApplicationStartError, match="another active launcher"):
        manager.cleanup_stale_processes()


def test_malformed_marker_never_authorizes_process_termination(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    marker = tmp_path / f"{app.id}.runtime.json"
    marker.write_text(json.dumps({"pid": 9876, "identity": None}), encoding="utf-8")
    monkeypatch.setattr(manager, "_process_identity", lambda pid: None)
    monkeypatch.setattr(
        manager,
        "_terminate_process_tree",
        lambda pid: pytest.fail("missing identity must fail closed"),
    )

    manager.cleanup_stale_processes()

    assert not marker.exists()


def test_records_process_state(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    state = manager.start(app, _env(tmp_path))
    assert state.process_id == 1234
    assert state.url.startswith("http://127.0.0.1:")
    assert state.url == f"http://127.0.0.1:{state.port}"


def test_does_not_start_duplicate_app(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    calls = []

    def popen(*args, **kwargs):
        calls.append(args)
        return FakeProcess()

    monkeypatch.setattr("subprocess.Popen", popen)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    first = manager.start(app, _env(tmp_path))
    second = manager.start(app, _env(tmp_path))
    assert first is second
    assert len(calls) == 1


def test_truncates_app_log_on_each_launch(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    processes = [FakeProcess(pid=1111), FakeProcess(pid=2222)]

    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: processes.pop(0))
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())

    manager.start(app, _env(tmp_path))
    log_path = tmp_path / f"{app.id}.log"
    log_path.write_text(log_path.read_text(encoding="utf-8") + "stale-port http://127.0.0.1:63076\n", encoding="utf-8")

    manager.stop(app.id)
    manager.start(app, _env(tmp_path))

    assert "stale-port" not in log_path.read_text(encoding="utf-8")


def test_restart_produces_new_pid_and_verified_url(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    processes = [FakeProcess(pid=1111), FakeProcess(pid=2222)]

    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: processes.pop(0))
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())

    first = manager.start(app, _env(tmp_path))
    second = manager.restart(app, _env(tmp_path))

    assert first.process_id == 1111
    assert second.process_id == 2222
    assert second.url == f"http://127.0.0.1:{second.port}"
    assert second.process.poll() is None


def test_stops_process(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    fake = FakeProcess()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    manager.start(app, _env(tmp_path))
    manager.stop(app.id)
    assert fake.terminated
    assert manager.get(app.id) is None


def test_kills_process_that_does_not_stop_before_timeout(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    fake = StubbornFakeProcess()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    manager.start(app, _env(tmp_path))

    manager.stop(app.id, timeout_seconds=0)

    assert fake.terminated
    assert fake.killed
    assert manager.get(app.id) is None


def test_cleans_state_after_crash(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    fake = FakeProcess()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    manager.start(app, _env(tmp_path))
    fake.terminated = True
    assert manager.get(app.id) is None


def test_mark_running_ignores_malformed_url(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    manager.start(app, _env(tmp_path))

    assert manager.mark_running_from_url(app.id, "http://127.0.0.1:bad") is None


@pytest.mark.parametrize("late_result", ["failure", "success"])
def test_old_startup_completion_cannot_stop_or_replace_restarted_app(monkeypatch, repo_root, tmp_path, late_result):
    app = discover_apps(repo_root / "apps")[0]
    environment = _env(tmp_path)
    first, replacement = FakeProcess(1111), FakeProcess(2222)
    processes = iter([first, replacement])
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: next(processes))
    manager = ProcessManager(tmp_path)
    monkeypatch.setattr(manager, "_process_identity", lambda pid: None)

    def health(process, port, *args):
        if process is first:
            manager.stop(app.id)
            manager.start(app, environment)
            if late_result == "failure":
                raise ApplicationHealthCheckError("old startup timed out")
        return f"http://127.0.0.1:{port}"

    monkeypatch.setattr(manager.health_checker, "wait_until_healthy", health)
    with pytest.raises((ApplicationStartError, ApplicationHealthCheckError)):
        manager.start(app, environment)
    assert manager.get(app.id).process is replacement
    assert not replacement.terminated


def test_null_process_identity_never_authorizes_tree_termination(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    fake = FakeProcess()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    monkeypatch.setattr(manager, "_process_identity", lambda pid: None)
    manager.start(app, _env(tmp_path))
    manager._runtime_marker_path(app.id).write_text(json.dumps({"pid": fake.pid, "identity": None}), encoding="utf-8")
    monkeypatch.setattr(manager, "_terminate_process_tree", lambda pid: pytest.fail("null identity must fail closed"))

    manager.stop(app.id)

    assert fake.terminated


def test_failed_stop_keeps_live_process_tracked(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    fake = FakeProcess()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    monkeypatch.setattr(manager, "_process_identity", lambda pid: None)
    state = manager.start(app, _env(tmp_path))

    def denied():
        raise PermissionError("simulated denied stop")

    monkeypatch.setattr(fake, "terminate", denied)
    with pytest.raises(ApplicationStopError, match="denied stop"):
        manager.stop(app.id)
    assert manager.get(app.id) is state
    assert state in manager.running_states()


def test_slow_stop_does_not_block_ui_state_reads(monkeypatch, repo_root, tmp_path):
    app = discover_apps(repo_root / "apps")[0]
    fake = FakeProcess()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake)
    manager = ProcessManager(tmp_path, health_checker=FakeHealth())
    monkeypatch.setattr(manager, "_process_identity", lambda pid: None)
    state = manager.start(app, _env(tmp_path))
    stopping, release = threading.Event(), threading.Event()

    def slow_terminate():
        stopping.set()
        assert release.wait(5)
        fake.terminated = True

    monkeypatch.setattr(fake, "terminate", slow_terminate)
    with ThreadPoolExecutor(max_workers=2) as executor:
        stop = executor.submit(manager.stop, app.id)
        try:
            assert stopping.wait(2)
            assert executor.submit(manager.running_states).result(timeout=1) == [state]
        finally:
            release.set()
        stop.result(timeout=2)
