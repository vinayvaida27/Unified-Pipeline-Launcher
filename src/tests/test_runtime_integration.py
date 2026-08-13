from __future__ import annotations

import sys
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from launcher.exceptions import ApplicationHealthCheckError
from launcher.models import (
    ApplicationManifest,
    EnvironmentState,
    LaunchSettings,
)
from launcher.process_manager import ProcessManager


pytestmark = pytest.mark.integration


def _app(tmp_path: Path, app_id: str, source: str, folder_name: str | None = None) -> ApplicationManifest:
    app_dir = tmp_path / (folder_name or app_id)
    app_dir.mkdir()
    entrypoint = app_dir / "app.py"
    entrypoint.write_text(source, encoding="utf-8")
    icon = app_dir / "icon.svg"
    icon.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    requirements = app_dir / "requirements.txt"
    requirements.write_text("streamlit>=1.40,<2\n", encoding="utf-8")
    return ApplicationManifest(
        schema_version=1,
        id=app_id,
        name=app_id,
        version="1.0.0",
        description="Integration fixture",
        category="Test",
        type="streamlit",
        entrypoint=entrypoint,
        icon=icon,
        requirements=requirements,
        wheelhouse=app_dir / "wheelhouse",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
        enabled=True,
        display_order=1,
        launch=LaunchSettings("127.0.0.1", "dynamic", True, "none", False, 20),
        app_dir=app_dir,
    )


def _environment(tmp_path: Path, app: ApplicationManifest) -> EnvironmentState:
    python = Path(sys.executable)
    return EnvironmentState(app.id, app.version, python.parent, python, True, tmp_path / "ready.json")


def test_real_streamlit_process_uses_app_cwd_and_scrubs_python_environment(tmp_path, monkeypatch):
    psutil = pytest.importorskip("psutil")
    monkeypatch.setenv("PYTHONPATH", "poison-pythonpath")
    monkeypatch.setenv("PYTHONHOME", "poison-pythonhome")
    app = _app(
        tmp_path,
        "runtime-probe",
        "import streamlit as st\nst.title('Runtime probe')\n",
    )
    manager = ProcessManager(tmp_path / "logs")
    try:
        state = manager.start(app, _environment(tmp_path, app))
        assert state.process_id
        child = psutil.Process(state.process_id)
        child_environment = child.environ()
        assert Path(child.cwd()) == app.app_dir
        assert Path(child.exe()) == Path(sys.executable)
        assert child_environment.get("PYTHONPATH") is None
        assert child_environment.get("PYTHONHOME") is None
        assert child_environment.get("PYTHONNOUSERSITE") == "1"
    finally:
        manager.stop_all()


def test_two_real_streamlit_apps_run_and_stop_independently(tmp_path):
    first = _app(tmp_path, "first-app", "import streamlit as st\nst.title('First app')\n")
    second = _app(tmp_path, "second-app", "import streamlit as st\nst.title('Second app')\n")
    manager = ProcessManager(tmp_path / "logs")
    try:
        first_state = manager.start(first, _environment(tmp_path, first))
        second_state = manager.start(second, _environment(tmp_path, second))
        assert first_state.port != second_state.port
        assert first_state.process.poll() is None
        assert second_state.process.poll() is None

        manager.stop(first.id, timeout_seconds=3)

        assert first_state.process.poll() is not None
        assert second_state.process.poll() is None
        assert manager.get(second.id) is second_state
    finally:
        manager.stop_all()


def test_process_manager_does_not_accept_an_unrelated_http_server_as_streamlit(tmp_path):
    app = _app(tmp_path, "occupied-port", "import streamlit as st\nst.title('Never starts here')\n")
    app = replace(app, launch=replace(app.launch, startup_timeout_seconds=3))
    manager = ProcessManager(tmp_path / "logs")

    class UnrelatedHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not streamlit")

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), UnrelatedHandler)
    occupied_port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    manager.port_manager.get_available_port = lambda: occupied_port  # type: ignore[method-assign]

    try:
        with pytest.raises(ApplicationHealthCheckError):
            manager.start(app, _environment(tmp_path, app))
        assert manager.get(app.id) is None
    finally:
        server.shutdown()
        server.server_close()
        manager.stop_all()


def test_real_launch_handles_windows_safe_path_metacharacters(tmp_path):
    app = _app(
        tmp_path,
        "path-probe",
        "import streamlit as st\nst.title('Path probe')\n",
        "space ünicode (hash# amp& apostrophe' semi;)",
    )
    manager = ProcessManager(tmp_path / "logs")
    try:
        state = manager.start(app, _environment(tmp_path, app))
        assert state.process.poll() is None
        assert state.entrypoint_path == app.entrypoint
    finally:
        manager.stop_all()


@pytest.mark.xfail(strict=True, reason="Windows CreateProcess rejects the long app directory as cwd")
def test_real_launch_handles_a_long_app_path(tmp_path):
    app = _app(
        tmp_path,
        "long-path-probe",
        "import streamlit as st\nst.title('Long path probe')\n",
        "long-" + ("x" * 180),
    )
    manager = ProcessManager(tmp_path / "logs")
    try:
        state = manager.start(app, _environment(tmp_path, app))
        assert len(str(app.entrypoint)) > 260
        assert state.process.poll() is None
    finally:
        manager.stop_all()


@pytest.mark.xfail(strict=True, reason="ProcessManager has no child-process persistence or reconciliation")
def test_new_process_manager_reconciles_a_child_from_an_earlier_launcher_instance(tmp_path):
    app = _app(tmp_path, "restart-probe", "import streamlit as st\nst.title('Restart probe')\n")
    original = ProcessManager(tmp_path / "logs")
    replacement = ProcessManager(tmp_path / "logs")

    try:
        state = original.start(app, _environment(tmp_path, app))
        assert state.process.poll() is None
        assert replacement.get(app.id) is not None
    finally:
        original.stop_all()
        replacement.stop_all()
