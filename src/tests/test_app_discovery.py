from __future__ import annotations

import json

import pytest

from launcher.app_discovery import discover_apps
from launcher.exceptions import ManifestValidationError


def _registry_path(apps_dir):
    return apps_dir / "apps.json"


def _load_registry(apps_dir):
    return json.loads(_registry_path(apps_dir).read_text(encoding="utf-8"))


def _write_registry(apps_dir, data):
    _registry_path(apps_dir).write_text(json.dumps(data), encoding="utf-8")


def test_discovers_all_10_apps(repo_root):
    apps = discover_apps(repo_root / "apps")
    assert len(apps) == 10


def test_sorts_by_display_order(repo_root):
    apps = discover_apps(repo_root / "apps")
    assert [app.display_order for app in apps] == list(range(1, 11))


def test_rejects_duplicate_ids(copied_apps):
    data = _load_registry(copied_apps)
    data["applications"][1]["id"] = "hello-pipeline"
    _write_registry(copied_apps, data)
    apps = discover_apps(copied_apps)
    assert len(apps) == 9


def test_handles_missing_icon(copied_apps):
    icon = copied_apps / "01_hello_pipeline" / "assets" / "icon.svg"
    icon.unlink()
    apps = discover_apps(copied_apps)
    app = next(app for app in apps if app.id == "hello-pipeline")
    assert app.icon == icon.resolve()
    assert not app.icon.exists()
    assert len(apps) == 10


@pytest.mark.parametrize("field", ["entrypoint", "icon", "requirements", "wheelhouse"])
def test_rejects_path_traversal(copied_apps, field):
    data = _load_registry(copied_apps)
    data["applications"][0][field] = "../../malicious.py"
    _write_registry(copied_apps, data)
    apps = discover_apps(copied_apps)
    assert all(app.id != "hello-pipeline" for app in apps)


def test_icon_field_remains_required(copied_apps):
    data = _load_registry(copied_apps)
    data["defaults"].pop("icon", None)
    data["applications"][0].pop("icon", None)
    _write_registry(copied_apps, data)
    assert all(app.id != "hello-pipeline" for app in discover_apps(copied_apps))


@pytest.mark.parametrize("filename", ["app.py", "requirements.txt"])
def test_missing_required_app_files_still_rejects_application(copied_apps, filename):
    (copied_apps / "01_hello_pipeline" / filename).unlink()
    assert all(app.id != "hello-pipeline" for app in discover_apps(copied_apps))


def test_skips_disabled_apps(copied_apps):
    data = _load_registry(copied_apps)
    data["applications"][0]["enabled"] = False
    _write_registry(copied_apps, data)
    apps = discover_apps(copied_apps)
    assert len(apps) == 9


def test_malformed_registry_raises_launcher_error(copied_apps):
    _registry_path(copied_apps).write_text("{not-json", encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="Could not read app registry"):
        discover_apps(copied_apps)
