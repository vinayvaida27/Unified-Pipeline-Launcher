from __future__ import annotations

import socket

from launcher.port_manager import PortManager


def test_returns_valid_port():
    port = PortManager().get_available_port()
    assert isinstance(port, int)
    assert port > 0


def test_supports_multiple_allocations():
    manager = PortManager()
    ports = {manager.get_available_port() for _ in range(5)}
    assert len(ports) == 5


def test_binds_only_to_localhost(monkeypatch):
    calls = []
    original_bind = socket.socket.bind

    def bind(self, address):
        calls.append(address)
        return original_bind(self, address)

    monkeypatch.setattr(socket.socket, "bind", bind)
    PortManager().get_available_port()
    assert calls
    assert all(call[0] == "127.0.0.1" for call in calls)
