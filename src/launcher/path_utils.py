"""Path and JSON utilities."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .exceptions import SecurityValidationError


def _expand_windows_vars(value: str) -> str:
    """Expand %VAR% style variables on any platform (ntpath does not on POSIX)."""

    def _replace(match: "re.Match[str]") -> str:
        name = match.group(1)
        return os.environ.get(name, match.group(0))

    return re.sub(r"%([^%]+)%", _replace, value)


def expand_path(value: str, base_dir: Path | None = None) -> Path:
    """Expand environment variables and return an absolute path."""

    expanded = os.path.expandvars(os.path.expanduser(value))
    expanded = _expand_windows_vars(expanded)
    path = Path(expanded)
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path.resolve()


def ensure_within_directory(path: Path, root: Path) -> Path:
    """Resolve a path and ensure it stays inside root."""

    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise SecurityValidationError(f"Path escapes approved directory: {path}") from exc
    return resolved


def reject_path_traversal(value: str) -> None:
    """Reject absolute paths and parent traversal in manifest-relative fields."""

    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SecurityValidationError(f"Unsafe relative path: {value}")


def read_json(path: Path) -> dict[str, Any]:
    """Read a UTF-8 JSON object."""

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON beside the target file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
