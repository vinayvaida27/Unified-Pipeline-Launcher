from __future__ import annotations

import json
import os

import pytest

from launcher.app_discovery import discover_apps
from launcher.path_utils import read_text_tail


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


def test_read_text_tail_bounds_large_file_read(tmp_path):
    path = tmp_path / "large.log"
    path.write_text(("x" * 100_000) + "tail-marker", encoding="utf-8")

    text = read_text_tail(path, 32)

    assert text.endswith("tail-marker")
    assert len(text.encode("utf-8")) <= 32


def test_rejects_entrypoint_symlink_escape(copied_apps, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("raise RuntimeError('must not execute')\n", encoding="utf-8")
    link = copied_apps / "01_hello_pipeline" / "symlink-app.py"
    try:
        os.symlink(outside, link)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    _mutate_first_registry_app(copied_apps, entrypoint="symlink-app.py")

    apps = discover_apps(copied_apps)

    assert all(app.id != "hello-pipeline" for app in apps)
