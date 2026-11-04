"""Application registry discovery and validation."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from .constants import DEFAULT_ADDRESS, SUPPORTED_APP_TYPES, SUPPORTED_SCHEMA_VERSION
from .exceptions import ManifestValidationError, SecurityValidationError
from .models import ApplicationManifest, LaunchSettings
from .path_utils import ensure_within_directory, read_json, reject_path_traversal
from .security import reject_command_injection_fields, validate_app_id

LOG = logging.getLogger(__name__)
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")


def _required(data: dict, key: str):
    if key not in data:
        raise ManifestValidationError(f"Missing required manifest field: {key}")
    return data[key]


def _merge_defaults(defaults: dict, app_data: dict) -> dict:
    data = {**defaults, **app_data}
    launch_defaults = defaults.get("launch", {})
    launch_data = app_data.get("launch", {})
    data["launch"] = {**launch_defaults, **launch_data}
    return data


def _manifest_from_registry_entry(apps_directory: Path, defaults: dict, app_data: dict) -> ApplicationManifest:
    """Build and validate an application manifest from apps/apps.json."""

    reject_command_injection_fields(app_data)
    data = _merge_defaults(defaults, app_data)
    folder_raw = str(_required(data, "folder"))
    reject_path_traversal(folder_raw)
    app_dir = ensure_within_directory(apps_directory / folder_raw, apps_directory)
    return _load_app_manifest_data(app_dir, data)


def load_app_manifest(app_dir: Path) -> ApplicationManifest:
    """Load and strictly validate a legacy per-app manifest."""

    data = read_json(app_dir / "app_manifest.json")
    reject_command_injection_fields(data)
    return _load_app_manifest_data(app_dir, data)


def _load_app_manifest_data(app_dir: Path, data: dict) -> ApplicationManifest:
    """Validate application metadata against files inside app_dir."""

    if int(data.get("schema_version", SUPPORTED_SCHEMA_VERSION)) != SUPPORTED_SCHEMA_VERSION:
        raise ManifestValidationError("Unsupported application schema version")
    app_id = str(_required(data, "id"))
    validate_app_id(app_id)
    version = str(_required(data, "version"))
    if not SEMVER.match(version):
        raise ManifestValidationError(f"Invalid semantic version: {version}")
    app_type = str(_required(data, "type"))
    if app_type not in SUPPORTED_APP_TYPES:
        raise ManifestValidationError(f"Unsupported app type: {app_type}")

    entrypoint_raw = str(_required(data, "entrypoint"))
    icon_raw = str(_required(data, "icon"))
    requirements_raw = str(_required(data, "requirements"))
    wheelhouse_raw = str(data.get("wheelhouse", "wheelhouse"))
    for value in (entrypoint_raw, icon_raw, requirements_raw, wheelhouse_raw):
        reject_path_traversal(value)

    entrypoint = ensure_within_directory(app_dir / entrypoint_raw, app_dir)
    icon = ensure_within_directory(app_dir / icon_raw, app_dir)
    requirements = ensure_within_directory(app_dir / requirements_raw, app_dir)
    wheelhouse = ensure_within_directory(app_dir / wheelhouse_raw, app_dir)

    if not entrypoint.is_file():
        raise ManifestValidationError(f"Entrypoint does not exist: {entrypoint}")
    if not icon.is_file():
        raise ManifestValidationError(f"Icon does not exist: {icon}")
    if not requirements.is_file():
        raise ManifestValidationError(f"Requirements file does not exist: {requirements}")
    display_order = int(_required(data, "display_order"))
    if display_order < 1:
        raise ManifestValidationError("display_order must be positive")

    launch_data = _required(data, "launch")
    address = str(launch_data.get("address", DEFAULT_ADDRESS))
    if address != DEFAULT_ADDRESS:
        raise ManifestValidationError("Streamlit apps must bind to 127.0.0.1")

    return ApplicationManifest(
        schema_version=int(data.get("schema_version", SUPPORTED_SCHEMA_VERSION)),
        id=app_id,
        name=str(_required(data, "name")),
        version=version,
        description=str(_required(data, "description")),
        category=str(_required(data, "category")),
        type=app_type,
        entrypoint=entrypoint,
        icon=icon,
        requirements=requirements,
        wheelhouse=wheelhouse,
        python_version=str(_required(data, "python_version")),
        enabled=bool(_required(data, "enabled")),
        display_order=display_order,
        launch=LaunchSettings(
            address=address,
            port=str(launch_data.get("port", "dynamic")),
            headless=bool(launch_data.get("headless", True)),
            file_watcher_type=str(launch_data.get("file_watcher_type", "none")),
            gather_usage_stats=bool(launch_data.get("gather_usage_stats", False)),
            startup_timeout_seconds=int(launch_data.get("startup_timeout_seconds", 60)),
        ),
        app_dir=app_dir.resolve(),
    )


def _discover_from_registry(apps_directory: Path, include_disabled: bool) -> list[ApplicationManifest]:
    registry_path = apps_directory / "apps.json"
    registry = read_json(registry_path)
    if registry.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ManifestValidationError("Unsupported app registry schema version")
    defaults = registry.get("defaults", {})
    discovered: list[ApplicationManifest] = []
    seen_ids: set[str] = set()
    for app_data in registry.get("applications", []):
        try:
            app = _manifest_from_registry_entry(apps_directory, defaults, app_data)
            if app.id in seen_ids:
                raise ManifestValidationError(f"Duplicate application ID: {app.id}")
            seen_ids.add(app.id)
            if app.enabled or include_disabled:
                discovered.append(app)
        except (ManifestValidationError, SecurityValidationError, ValueError) as exc:
            LOG.exception("Skipping invalid application registry entry in %s: %s", registry_path, exc)
    return discovered


def _discover_from_legacy_manifests(apps_directory: Path, include_disabled: bool) -> list[ApplicationManifest]:
    discovered: list[ApplicationManifest] = []
    seen_ids: set[str] = set()
    for manifest_path in sorted(apps_directory.glob("*/app_manifest.json")):
        try:
            app = load_app_manifest(manifest_path.parent.resolve())
            if app.id in seen_ids:
                raise ManifestValidationError(f"Duplicate application ID: {app.id}")
            seen_ids.add(app.id)
            if app.enabled or include_disabled:
                discovered.append(app)
        except (ManifestValidationError, SecurityValidationError, ValueError) as exc:
            LOG.exception("Skipping invalid application manifest at %s: %s", manifest_path, exc)
    return discovered


def discover_apps(apps_directory: Path, include_disabled: bool = False) -> list[ApplicationManifest]:
    """Discover valid apps from apps/apps.json, with legacy manifest fallback."""

    if not apps_directory.exists():
        LOG.warning("Applications directory does not exist: %s", apps_directory)
        return []
    if (apps_directory / "apps.json").exists():
        discovered = _discover_from_registry(apps_directory, include_disabled)
    else:
        discovered = _discover_from_legacy_manifests(apps_directory, include_disabled)
    return sorted(discovered, key=lambda app: (app.display_order, app.name.lower()))
