"""Small, atomic updates to the application registry."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .exceptions import LauncherError
from .path_utils import read_json


def set_app_archived(registry_path: Path, app_id: str, archived: bool) -> None:
    """Persist one app's archive state without rewriting unrelated registry data."""

    registry = read_json(registry_path)
    for app in registry.get("applications", []):
        if app.get("id") == app_id:
            app["archived"] = archived
            temporary = registry_path.with_suffix(registry_path.suffix + ".tmp")
            temporary.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
            temporary.replace(registry_path)
            return
    raise LauncherError(f"Application is not registered: {app_id}")


def add_application(registry_path: Path, entry: dict) -> str:
    """Append one application while preserving the latest registry contents."""

    try:
        registry = read_json(registry_path)
        applications = registry.setdefault("applications", [])
        new_path = os.path.normcase(str(Path(entry["path"]).expanduser().resolve()))
        for app in applications:
            raw_path = app.get("path") or app.get("app_path")
            if raw_path:
                try:
                    existing_path = os.path.normcase(str(Path(raw_path).expanduser().resolve()))
                except (OSError, RuntimeError):
                    existing_path = os.path.normcase(str(raw_path))
                if existing_path == new_path:
                    raise LauncherError("An application with this Python path is already registered.")
        applications.append(entry)
        temporary = registry_path.with_suffix(registry_path.suffix + ".tmp")
        try:
            temporary.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, registry_path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return str(entry["id"])
    except LauncherError:
        raise
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise LauncherError(f"Could not update application registry: {exc}") from exc
