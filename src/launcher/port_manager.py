"""Dynamic localhost port allocation."""

from __future__ import annotations

import socket
from contextlib import closing

from .constants import DEFAULT_ADDRESS


class PortManager:
    """Allocates available localhost TCP ports."""

    def __init__(self) -> None:
        self._allocated: set[int] = set()

    def get_available_port(self) -> int:
        """Return an available dynamic port bound on 127.0.0.1."""

        for _ in range(20):
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.bind((DEFAULT_ADDRESS, 0))
                port = int(sock.getsockname()[1])
            if port not in self._allocated and self.is_available(port):
                self._allocated.add(port)
                return port
        raise RuntimeError("Unable to allocate a free localhost port")

    def is_available(self, port: int) -> bool:
        """Check whether a port can currently be bound."""

        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind((DEFAULT_ADDRESS, port))
            except OSError:
                return False
        return True

    def release(self, port: int | None) -> None:
        """Release a tracked port."""

        if port is not None:
            self._allocated.discard(port)
