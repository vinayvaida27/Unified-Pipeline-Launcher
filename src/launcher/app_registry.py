"""Small, atomic updates to the application registry."""

from __future__ import annotations

import json
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
