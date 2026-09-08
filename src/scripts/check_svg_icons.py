"""Check registered application icons and launcher assets with the actual Qt parser."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from launcher.app_discovery import discover_apps
from launcher.ui.svg import safe_svg_pixmap


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    qt_app = QApplication.instance() or QApplication([])
    # Discover only registered icons; backups and malformed test fixtures are not assets.
    paths = {app.icon for app in discover_apps(root / "apps") if app.icon.suffix.lower() == ".svg"}
    paths.update((root / "src/assets").rglob("*.svg"))
    bad = [path for path in sorted(paths) if safe_svg_pixmap(path).isNull()]
    print(f"SVG icons checked: {len(paths)}; rejected: {len(bad)}")
    for path in bad:
        print(path)
    assert qt_app is not None
    return int(bool(bad))


if __name__ == "__main__":
    sys.exit(main())
