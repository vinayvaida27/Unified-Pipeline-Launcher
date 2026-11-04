from __future__ import annotations

import json

from launcher.app_discovery import discover_apps


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
    (copied_apps / "01_hello_pipeline" / "assets" / "icon.svg").unlink()
    apps = discover_apps(copied_apps)
    assert all(app.id != "hello-pipeline" for app in apps)


def test_rejects_path_traversal(copied_apps):
    data = _load_registry(copied_apps)
    data["applications"][0]["entrypoint"] = "../../malicious.py"
    _write_registry(copied_apps, data)
    apps = discover_apps(copied_apps)
    assert all(app.id != "hello-pipeline" for app in apps)


def test_skips_disabled_apps(copied_apps):
    data = _load_registry(copied_apps)
    data["applications"][0]["enabled"] = False
    _write_registry(copied_apps, data)
    apps = discover_apps(copied_apps)
    assert len(apps) == 9


def test_discovers_direct_python_path_without_optional_files(copied_apps, tmp_path):
    entrypoint = tmp_path / "external_pipeline.py"
    entrypoint.write_text("import streamlit as st\nst.write('external')\n", encoding="utf-8")
    data = _load_registry(copied_apps)
    data["applications"].append(
        {
            "id": "external-pipeline",
            "path": str(entrypoint),
            "name": "External Pipeline",
            "version": "1.0.0",
            "description": "A Streamlit file outside the apps directory.",
            "category": "External",
            "display_order": 11,
        }
    )
    _write_registry(copied_apps, data)

    app = next(app for app in discover_apps(copied_apps) if app.id == "external-pipeline")
    assert app.entrypoint == entrypoint.resolve()
    assert app.requirements is None
    assert app.icon.name == "launcher.png"
