from __future__ import annotations

import json

from launcher.app_discovery import discover_apps


def _mutate_first_registry_app(apps_dir, **updates):
    registry = apps_dir / "apps.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["applications"][0].update(updates)
    registry.write_text(json.dumps(data), encoding="utf-8")


def test_rejects_parent_traversal(copied_apps):
    _mutate_first_registry_app(copied_apps, entrypoint="../app.py")
    apps = discover_apps(copied_apps)
    assert all(app.id != "hello-pipeline" for app in apps)


def test_rejects_absolute_entrypoint_outside_app_root(copied_apps, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("", encoding="utf-8")
    _mutate_first_registry_app(copied_apps, entrypoint=str(outside))
    apps = discover_apps(copied_apps)
    assert all(app.id != "hello-pipeline" for app in apps)


def test_rejects_command_injection_fields(copied_apps):
    _mutate_first_registry_app(copied_apps, command="calc.exe")
    apps = discover_apps(copied_apps)
    assert all(app.id != "hello-pipeline" for app in apps)


def test_rejects_invalid_app_ids(copied_apps):
    _mutate_first_registry_app(copied_apps, id="Hello Pipeline; calc")
    apps = discover_apps(copied_apps)
    assert all(app.name != "Hello Pipeline" for app in apps)
