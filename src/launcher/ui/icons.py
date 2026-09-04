"""Consistent high-DPI icons for launcher controls."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon, QPainter


def _icon_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "assets" / "icons" / "lucide"
    return Path(__file__).resolve().parents[2] / "assets" / "icons" / "lucide"


@lru_cache(maxsize=64)
def ui_icon(name: str, color: str, size: int = 18) -> QIcon:
    """Load and tint a packaged Lucide icon for light or dark controls."""

    source = QIcon(str(_icon_directory() / f"{name}.svg"))
    if source.isNull():
        return QIcon()

    result = QIcon()
    for scale in (1, 2):
        pixmap = source.pixmap(QSize(size * scale, size * scale))
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        result.addPixmap(pixmap)
    return result
