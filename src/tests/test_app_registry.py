from __future__ import annotations

import json

import pytest

from launcher.app_registry import add_application
from launcher.exceptions import LauncherError


def _entry(path):
    return {"id": "new-app", "path": str(path), "name": "New App"}


def test_add_application_preserves_existing_entries(tmp_path):
    registry = tmp_path / "apps.json"
    registry.write_text(json.dumps({"schema_version": 1, "applications": [{"id": "old"}]}), encoding="utf-8")
    script = tmp_path / "app.py"
    script.write_text("", encoding="utf-8")

    assert add_application(registry, _entry(script)) == "new-app"
    data = json.loads(registry.read_text(encoding="utf-8"))
    assert [item["id"] for item in data["applications"]] == ["old", "new-app"]


def test_add_application_rejects_duplicate_path(tmp_path):
    script = tmp_path / "app.py"
    script.write_text("", encoding="utf-8")
    registry = tmp_path / "apps.json"
    registry.write_text(json.dumps({"applications": [{"id": "old", "path": str(script)}]}), encoding="utf-8")

    with pytest.raises(LauncherError, match="already registered"):
        add_application(registry, _entry(script))


def test_add_application_reports_write_failure(tmp_path, monkeypatch):
    registry = tmp_path / "apps.json"
    registry.write_text(json.dumps({"applications": []}), encoding="utf-8")
    script = tmp_path / "app.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr("launcher.app_registry.os.replace", lambda *args: (_ for _ in ()).throw(OSError("read-only")))

    with pytest.raises(LauncherError, match="Could not update"):
        add_application(registry, _entry(script))
