"""Render application SVGs with visible fallbacks for Qt parser warnings."""

from __future__ import annotations

import logging
import sys
import threading
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, qFormatLogMessage, qInstallMessageHandler
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


LOG = logging.getLogger(__name__)
_RENDER_LOCK = threading.RLock()


@lru_cache(maxsize=256)
def _warn_once(path: str, reason: str) -> None:
    LOG.warning("Cannot render SVG %s: %s. Using icon fallback; replace or repair this icon.", path, reason)


def safe_svg_pixmap(path: Path, size: int = 42) -> QPixmap:
    """Return a null pixmap if Qt rejects or partially accepts an SVG.

    Call on the GUI thread. Qt's handler is process-wide, so serialize our
    temporary handlers and forward messages unrelated to this SVG render.
    """

    try:
        data = path.read_bytes()
    except OSError as exc:
        _warn_once(str(path), str(exc)[:200])
        return QPixmap()

    warnings: list[str] = []
    render_thread = threading.get_ident()

    def handle_message(kind, context, message):
        if threading.get_ident() == render_thread and context.category.startswith("qt.svg"):
            if not warnings:
                warnings.append(message[:200])
        elif previous is not None:
            previous(kind, context, message)
        elif sys.stderr is not None:
            sys.stderr.write(qFormatLogMessage(kind, context, message) + "\n")

    pixmap = QPixmap()
    with _RENDER_LOCK:
        previous = qInstallMessageHandler(handle_message)
        try:
            renderer = QSvgRenderer(QByteArray(data))
            if renderer.isValid() and not warnings:
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                try:
                    renderer.render(painter)
                finally:
                    painter.end()
        finally:
            qInstallMessageHandler(previous)

    if warnings or pixmap.isNull():
        _warn_once(str(path), warnings[0] if warnings else "invalid SVG XML or document")
        return QPixmap()
    return pixmap
