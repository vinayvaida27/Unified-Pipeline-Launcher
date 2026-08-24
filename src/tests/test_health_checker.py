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


def test_healthy_endpoint_does_not_depend_on_streamlit_log_wording(tmp_path, monkeypatch):
    port = PortManager().get_available_port()
    log_path = tmp_path / "app.log"
    log_path.write_text("Streamlit logging format changed\n", encoding="utf-8")
    monkeypatch.setattr(HealthChecker, "_url_ok", staticmethod(lambda url: True))

    url = HealthChecker().wait_until_healthy(FakeProcess(), port, 1, log_path)

    assert url == f"http://127.0.0.1:{port}"


def test_stale_log_port_does_not_block_current_healthy_endpoint(tmp_path, monkeypatch):
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


def test_port_parser_ignores_bad_ports():
    assert HealthChecker._port_from_url("http://127.0.0.1:bad") is None
