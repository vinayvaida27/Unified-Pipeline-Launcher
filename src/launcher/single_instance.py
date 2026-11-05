"""Small Qt-native single-instance guard for the desktop launcher."""

from __future__ import annotations

import getpass
import hashlib
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def instance_name(root: Path) -> str:
    key = f"{getpass.getuser()}\0{root.resolve()}".encode("utf-8", "surrogatepass")
    return "UnifiedPipelineLauncher-" + hashlib.sha256(key).hexdigest()[:24]


class SingleInstance:
    def __init__(self, root: Path, on_activate: Callable[[], None]) -> None:
        self.name = instance_name(root)
        self._server = QLocalServer()
        self._on_activate = on_activate

    def acquire(self) -> bool:
        probe = QLocalSocket()
        probe.connectToServer(self.name)
        if probe.waitForConnected(1000):
            probe.write(QByteArray(b"activate"))
            probe.waitForBytesWritten(1000)
            probe.disconnectFromServer()
            return False
        QLocalServer.removeServer(self.name)
        if not self._server.listen(self.name):
            return False
        self._server.newConnection.connect(self._handle_connection)
        return True

    def _handle_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is not None:
                self._on_activate()
                socket.disconnectFromServer()

