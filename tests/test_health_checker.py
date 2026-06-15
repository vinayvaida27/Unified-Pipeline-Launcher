from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from launcher.exceptions import ApplicationHealthCheckError
from launcher.health_checker import HealthChecker
from launcher.port_manager import PortManager


class FakeProcess:
    def __init__(self, exit_code=None):
        self.exit_code = exit_code

    def poll(self):
        return self.exit_code


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        return


def test_succeeds_when_endpoint_becomes_healthy():
    port = PortManager().get_available_port()
    server = HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = HealthChecker().wait_until_healthy(FakeProcess(), port, 2)
        assert url == f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


def test_fails_on_timeout():
    port = PortManager().get_available_port()
    with pytest.raises(ApplicationHealthCheckError):
        HealthChecker().wait_until_healthy(FakeProcess(), port, 1)


def test_fails_when_process_exits():
    port = PortManager().get_available_port()
    with pytest.raises(ApplicationHealthCheckError):
        HealthChecker().wait_until_healthy(FakeProcess(exit_code=2), port, 1)


def test_succeeds_when_streamlit_log_reports_ready(tmp_path, monkeypatch):
    port = PortManager().get_available_port()
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "You can now view your Streamlit app in your browser.\n"
        f"URL: http://127.0.0.1:{port}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(HealthChecker, "_url_ok", staticmethod(lambda url: url == f"http://127.0.0.1:{port}/_stcore/health"))
    url = HealthChecker().wait_until_healthy(FakeProcess(), port, 1, log_path)
    assert url == f"http://127.0.0.1:{port}"


def test_old_log_port_never_replaces_current_allocated_port(tmp_path, monkeypatch):
    requested_port = PortManager().get_available_port()
    stale_port = PortManager().get_available_port()
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "You can now view your Streamlit app in your browser.\n"
        f"URL: http://127.0.0.1:{stale_port}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        HealthChecker,
        "_url_ok",
        staticmethod(lambda url: url == f"http://127.0.0.1:{requested_port}/_stcore/health"),
    )
    url = HealthChecker().wait_until_healthy(FakeProcess(), requested_port, 1, log_path)
    assert url == f"http://127.0.0.1:{requested_port}"


def test_log_parser_ignores_urls_from_other_ports(tmp_path):
    expected_port = PortManager().get_available_port()
    stale_port = PortManager().get_available_port()
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "You can now view your Streamlit app in your browser.\n"
        f"URL: http://127.0.0.1:{stale_port}\n",
        encoding="utf-8",
    )

    assert HealthChecker.streamlit_ready_url_from_log(log_path, expected_port=expected_port) is None
