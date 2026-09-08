from __future__ import annotations

import logging

import pytest

from PySide6.QtCore import QByteArray, qInstallMessageHandler, qWarning
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from launcher.app_discovery import discover_apps
from launcher.ui.app_card import AppCard, _safe_icon_pixmap


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication(["svg-regression", "-platform", "offscreen"])
    yield app


@pytest.mark.parametrize(
    "source",
    [
        "<svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="42" height="42"><path d="M0 0 L1,2,3"/></svg>',
    ],
    ids=["invalid-xml", "partially-accepted-path"],
)
def test_bad_svg_uses_fallback_with_one_actionable_warning(qt_app, tmp_path, caplog, source):
    path = tmp_path / "bad icon [ü].svg"
    path.write_text(source, encoding="utf-8")
    qt_messages = []
    previous = qInstallMessageHandler(lambda kind, context, message: qt_messages.append(message))
    try:
        with caplog.at_level(logging.WARNING):
            assert _safe_icon_pixmap(path).isNull()
            assert _safe_icon_pixmap(path).isNull()
        qWarning("unrelated warning must still reach previous handler")
    finally:
        qInstallMessageHandler(previous)
    warnings = [record.message for record in caplog.records if str(path) in record.message]
    assert len(warnings) == 1
    assert "fallback" in warnings[0].lower()
    assert qt_messages == ["unrelated warning must still reach previous handler"]


def test_partial_svg_fixture_is_valid_to_qt_but_warns(qt_app):
    warnings = []
    previous = qInstallMessageHandler(lambda kind, context, message: warnings.append((context.category, message)))
    try:
        renderer = QSvgRenderer(QByteArray(b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0 L1,2,3"/></svg>'))
        assert renderer.isValid()
    finally:
        qInstallMessageHandler(previous)
    assert any(category == "qt.svg" and "path" in message for category, message in warnings)


def test_missing_svg_falls_back_and_valid_svg_renders(qt_app, tmp_path):
    assert _safe_icon_pixmap(tmp_path / "missing.svg").isNull()
    path = tmp_path / "valid.svg"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="42" height="42"><rect width="42" height="42" fill="red"/></svg>', encoding="utf-8")
    pixmap = _safe_icon_pixmap(path)
    assert not pixmap.isNull()
    assert pixmap.toImage().pixelColor(20, 20).name() == "#ff0000"


@pytest.mark.parametrize("missing", [True, False], ids=["missing-icon", "malformed-path"])
def test_registry_app_displays_letter_fallback(qt_app, copied_apps, caplog, missing):
    original = discover_apps(copied_apps)[0]
    path = original.icon
    if missing:
        path.unlink()
    else:
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0 L1,2,3"/></svg>', encoding="utf-8")
    discovered = {app.id: app for app in discover_apps(copied_apps)}
    assert original.id in discovered, "A missing icon must not hide an otherwise valid app"
    app = discovered[original.id]
    with caplog.at_level(logging.WARNING):
        cards = [AppCard(app), AppCard(app)]
    try:
        for card in cards:
            assert card.icon_label.objectName() == "appIconFallback"
            assert card.icon_label.text() == app.name[0].upper()
        warnings = [record.message for record in caplog.records if str(path) in record.message]
        assert len(warnings) == 1
        assert "fallback" in warnings[0].lower()
    finally:
        for card in cards:
            card.close()
