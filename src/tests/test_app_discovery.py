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
    app = next(app for app in apps if app.id == "hello-pipeline")
    assert app.icon.name == "launcher.png"


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


def test_discovers_project_path_and_infers_requirements(copied_apps, tmp_path):
    project = tmp_path / "external_project"
    project.mkdir()
    entrypoint = project / "app.py"
    entrypoint.write_text("import pandas\nimport streamlit as st\nst.write('external')\n", encoding="utf-8")
    data = _load_registry(copied_apps)
    data["applications"].append(
        {
            "id": "external-project",
            "project_path": str(project),
            "name": "External Project",
            "version": "1.0.0",
            "description": "A project directory outside apps/.",
            "category": "External",
            "display_order": 12,
        }
    )
    _write_registry(copied_apps, data)

    app = next(app for app in discover_apps(copied_apps) if app.id == "external-project")
    assert app.entrypoint == entrypoint.resolve()
    assert app.icon.name == "launcher.png"
    assert app.requirements == (project / ".launcher-requirements.txt").resolve()
    assert app.requirements.read_text(encoding="utf-8") == "pandas\n"


def test_explicit_requirement_and_icon_paths_are_used(copied_apps, tmp_path):
    project = tmp_path / "explicit_project"
    project.mkdir()
    entrypoint = project / "main.py"
    requirements = tmp_path / "requirements-custom.txt"
    icon = tmp_path / "icon.svg"
    entrypoint.write_text("import streamlit as st\n", encoding="utf-8")
    requirements.write_text("streamlit\n", encoding="utf-8")
    icon.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='1' height='1' />", encoding="utf-8")
    data = _load_registry(copied_apps)
    data["applications"].append(
        {
            "id": "explicit-project",
            "project_path": str(project),
            "app_path": str(entrypoint),
            "requirements_path": str(requirements),
            "icon_path": str(icon),
            "name": "Explicit Project",
            "version": "1.0.0",
            "description": "Explicit paths.",
            "category": "External",
            "display_order": 13,
        }
    )
    _write_registry(copied_apps, data)

    app = next(app for app in discover_apps(copied_apps) if app.id == "explicit-project")
    assert app.entrypoint == entrypoint.resolve()
    assert app.requirements == requirements.resolve()
    assert app.icon == icon.resolve()
