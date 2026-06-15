"""Security validation helpers."""

from __future__ import annotations

import re

from .exceptions import SecurityValidationError

APP_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_app_id(app_id: str) -> None:
    """Validate a manifest application ID."""

    if not APP_ID_PATTERN.match(app_id):
        raise SecurityValidationError(f"Invalid app ID: {app_id}")


def reject_command_injection_fields(data: dict) -> None:
    """Reject manifest fields that attempt to define arbitrary commands."""

    forbidden = {"command", "args", "shell", "executable"}
    present = forbidden.intersection(data)
    if present:
        raise SecurityValidationError(f"Forbidden manifest command fields: {', '.join(sorted(present))}")
