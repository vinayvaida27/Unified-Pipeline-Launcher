"""Application registry discovery and validation."""

from __future__ import annotations

import logging
import ast
import re
import sys
from pathlib import Path

from .constants import DEFAULT_ADDRESS, SUPPORTED_APP_TYPES, SUPPORTED_SCHEMA_VERSION, SUPPORTED_REGISTRY_SCHEMA_VERSIONS
from .exceptions import ManifestValidationError, SecurityValidationError
from .models import ApplicationManifest, LaunchSettings
from .path_utils import ensure_within_directory, expand_path, read_json, reject_path_traversal
from .security import reject_command_injection_fields, validate_app_id

LOG = logging.getLogger(__name__)
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")
_V2_REGISTRY_KEYS = {"schema_version", "defaults", "policies", "applications"}
_V2_APP_KEYS = {"id", "source", "display", "runtime", "launch", "version", "name", "description", "category", "display_order", "enabled", "archived", "type"}
_V2_SOURCE_KEYS = {"folder", "project", "project_path", "entrypoint", "path", "requirements", "requirements_path", "icon", "icon_path"}
_V2_DISPLAY_KEYS = {"name", "description", "category", "order", "enabled", "archived"}
_V2_RUNTIME_KEYS = {"environment", "python_version"}


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


def _default_icon_path() -> Path:
    """Return the packaged launcher icon used when an app has no icon."""

    return Path(__file__).resolve().parents[1] / "assets" / "launcher" / "launcher.png"


def _resolve_direct_entrypoint(raw: str, apps_directory: Path) -> Path:
    """Resolve a direct app path from the registry or its parent directory."""

    path = Path(raw)
    if path.is_absolute():
        return expand_path(raw)
    for base in (apps_directory, apps_directory.parent):
        candidate = expand_path(raw, base)
        if candidate.is_file():
            return candidate
    return expand_path(raw, apps_directory)


def _resolve_registry_path(raw: str, apps_directory: Path) -> Path:
    """Resolve a registry path relative to apps/ or the repository root."""

    path = Path(str(raw))
    if path.is_absolute():
        return expand_path(str(raw))
    for base in (apps_directory, apps_directory.parent):
        candidate = expand_path(str(raw), base)
        if candidate.exists():
            return candidate
    return expand_path(str(raw), apps_directory)


def _validate_v2_allowed_path(raw: str, apps_directory: Path, policies: dict) -> None:
    """Validate external v2 paths without changing mapped/UNC spelling."""
    if not Path(str(raw)).is_absolute():
        if ".." in Path(str(raw)).parts:
            raise SecurityValidationError(f"Unsafe v2 relative path: {raw}")
        return
    if not bool(policies.get("allow_external_paths", False)):
        raise SecurityValidationError(f"External paths are disabled by registry policy: {raw}")
    roots = policies.get("allowed_roots", [])
    if roots:
        candidate = expand_path(str(raw))
        allowed = [expand_path(str(root), apps_directory.parent) for root in roots]
        if not any(candidate == root or root in candidate.parents for root in allowed):
            raise SecurityValidationError(f"Path is outside approved roots: {raw}")


def _normalize_v2_entry(apps_directory: Path, defaults: dict, app_data: dict, policies: dict) -> dict:
    """Translate a strict v2 entry into the existing flat manifest shape."""
    unknown = set(app_data) - _V2_APP_KEYS
    if unknown:
        raise ManifestValidationError(f"Unknown v2 application fields: {', '.join(sorted(unknown))}")
    source = app_data.get("source")
    if not isinstance(source, dict):
        raise ManifestValidationError("Schema v2 applications require a source object")
    unknown_source = set(source) - _V2_SOURCE_KEYS
    if unknown_source:
        raise ManifestValidationError(f"Unknown v2 source fields: {', '.join(sorted(unknown_source))}")
    locations = [key for key in ("folder", "project", "project_path", "entrypoint", "path") if source.get(key) not in (None, "")]
    if len(locations) != 1:
        raise ManifestValidationError("v2 source must contain exactly one of folder, project, entrypoint, or path")
    display = app_data.get("display", {})
    runtime = app_data.get("runtime", {})
    launch = app_data.get("launch", {})
    if not isinstance(display, dict) or not isinstance(runtime, dict) or not isinstance(launch, dict):
        raise ManifestValidationError("v2 display, runtime, and launch fields must be objects")
    if set(display) - _V2_DISPLAY_KEYS:
        raise ManifestValidationError(f"Unknown v2 display fields: {', '.join(sorted(set(display) - _V2_DISPLAY_KEYS))}")
    if set(runtime) - _V2_RUNTIME_KEYS:
        raise ManifestValidationError(f"Unknown v2 runtime fields: {', '.join(sorted(set(runtime) - _V2_RUNTIME_KEYS))}")
    for raw in (source.get(locations[0]), source.get("requirements"), source.get("requirements_path"), source.get("icon"), source.get("icon_path")):
        if raw:
            _validate_v2_allowed_path(str(raw), apps_directory, policies)
    launch_defaults = defaults.get("launch", {})
    runtime_defaults = defaults.get("runtime", {})
    source_defaults = defaults.get("source", {})
    merged = {
        **defaults,
        **app_data,
        "schema_version": 2,
        "id": app_data.get("id"),
        "name": display.get("name", app_data.get("name")),
        "description": display.get("description", app_data.get("description", "")),
        "category": display.get("category", app_data.get("category", "General")),
        "display_order": display.get("order", app_data.get("display_order")),
        "enabled": display.get("enabled", app_data.get("enabled", True)),
        "archived": display.get("archived", app_data.get("archived", False)),
        "version": app_data.get("version", "1.0.0"),
        "type": app_data.get("type", defaults.get("type", "streamlit")),
        "launch": {**launch_defaults, **launch},
        "python_version": runtime.get("python_version", runtime_defaults.get("python_version", defaults.get("python_version", "3.11"))),
    }
    location = locations[0]
    if location in {"entrypoint", "path"}:
        merged["path"] = source[location]
    else:
        merged["project_path"] = source[location]
        merged["entrypoint"] = source.get("entrypoint", source_defaults.get("entrypoint", "app.py"))
    merged["requirements_path"] = source.get("requirements", source.get("requirements_path", source_defaults.get("requirements")))
    merged["icon_path"] = source.get("icon", source.get("icon_path", source_defaults.get("icon")))
    merged["wheelhouse"] = defaults.get("wheelhouse", "wheelhouse")
    merged["runtime_environment"] = runtime.get("environment", runtime_defaults.get("environment", "shared"))
    if merged["runtime_environment"] not in {"shared", "auto", "isolated", "per_app"}:
        raise ManifestValidationError("runtime.environment must be shared, auto, or isolated")
    return merged


def _infer_requirements(entrypoint: Path) -> Path | None:
    """Write a small deterministic requirements file from imports when needed."""

    try:
        tree = ast.parse(entrypoint.read_text(encoding="utf-8"), filename=str(entrypoint))
    except (OSError, UnicodeError, SyntaxError):
        return None
    stdlib = getattr(sys, "stdlib_module_names", set())
    aliases = {"PIL": "Pillow", "cv2": "opencv-python", "sklearn": "scikit-learn", "yaml": "PyYAML"}
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".", 1)[0])
    packages = sorted(
        aliases.get(name, name)
        for name in modules
        if name not in stdlib
        and name not in {"streamlit"}
        and not (entrypoint.parent / f"{name}.py").exists()
        and not (entrypoint.parent / name).is_dir()
    )
    if not packages:
        return None
    generated = entrypoint.parent / ".launcher-requirements.txt"
    try:
        content = "\n".join(packages) + "\n"
        if not generated.exists() or generated.read_text(encoding="utf-8") != content:
            generated.write_text(content, encoding="utf-8")
    except OSError:
        return None
    return generated


def _manifest_from_registry_entry(apps_directory: Path, defaults: dict, app_data: dict) -> ApplicationManifest:
    """Build and validate an application manifest from apps/apps.json."""

    reject_command_injection_fields(app_data)
    data = _merge_defaults(defaults, app_data)
    project_raw = app_data.get("project_path") or app_data.get("project")
    direct_raw = app_data.get("path") or app_data.get("app_path")
    direct_raw = direct_raw or (
        app_data.get("entrypoint")
        if Path(str(app_data.get("entrypoint", ""))).is_absolute()
        else None
    )
    if project_raw or direct_raw:
        project = _resolve_registry_path(str(project_raw), apps_directory) if project_raw else None
        direct_path = _resolve_registry_path(str(direct_raw), apps_directory) if direct_raw else None
        if direct_path and direct_path.is_dir():
            project = direct_path
            direct_path = None
        if project:
            app_dir = project.resolve()
            candidate = app_data.get("entrypoint") or app_data.get("app_path") or "app.py"
            entrypoint = _resolve_registry_path(str(candidate), app_dir) if not Path(str(candidate)).is_absolute() else expand_path(str(candidate))
            if not entrypoint.is_file() and not app_data.get("entrypoint") and not app_data.get("app_path"):
                py_files = sorted(app_dir.glob("*.py"))
                entrypoint = py_files[0] if len(py_files) == 1 else entrypoint
        else:
            entrypoint = direct_path or _resolve_direct_entrypoint(str(direct_raw), apps_directory)
            app_dir = entrypoint.parent
        return _load_app_manifest_data(app_dir, data, direct_entrypoint=entrypoint)
    folder_raw = str(data.get("folder", data.get("project_path", "")))
    if not folder_raw:
        raise ManifestValidationError("Missing application project path: folder or project_path")
    reject_path_traversal(folder_raw)
    app_dir = ensure_within_directory(apps_directory / folder_raw, apps_directory)
    return _load_app_manifest_data(app_dir, data)


def load_app_manifest(app_dir: Path) -> ApplicationManifest:
    """Load and strictly validate a legacy per-app manifest."""

    data = read_json(app_dir / "app_manifest.json")
    reject_command_injection_fields(data)
    return _load_app_manifest_data(app_dir, data)


def _load_app_manifest_data(app_dir: Path, data: dict, direct_entrypoint: Path | None = None) -> ApplicationManifest:
    """Validate application metadata against files inside app_dir."""

    if int(data.get("schema_version", SUPPORTED_SCHEMA_VERSION)) not in SUPPORTED_REGISTRY_SCHEMA_VERSIONS:
        raise ManifestValidationError("Unsupported application schema version")
    app_id = str(_required(data, "id"))
    validate_app_id(app_id)
    version = str(_required(data, "version"))
    if not SEMVER.match(version):
        raise ManifestValidationError(f"Invalid semantic version: {version}")
    app_type = str(_required(data, "type"))
    if app_type not in SUPPORTED_APP_TYPES:
        raise ManifestValidationError(f"Unsupported app type: {app_type}")

    direct = direct_entrypoint is not None
    entrypoint_raw = str(data.get("entrypoint", ""))
    icon_raw = str(data.get("icon_path", data.get("icon", "")))
    requirements_raw = str(data.get("requirements_path", data.get("requirements", "")))
    wheelhouse_raw = str(data.get("wheelhouse", "wheelhouse"))
    if direct:
        entrypoint = direct_entrypoint.resolve()
        icon = expand_path(icon_raw, app_dir) if icon_raw else _default_icon_path()
        requirements = expand_path(requirements_raw, app_dir) if requirements_raw else None
        wheelhouse = expand_path(wheelhouse_raw, app_dir)
    else:
        for value in (entrypoint_raw, wheelhouse_raw):
            reject_path_traversal(value)
        if icon_raw and not Path(icon_raw).is_absolute():
            reject_path_traversal(icon_raw)
        if requirements_raw and not Path(requirements_raw).is_absolute():
            reject_path_traversal(requirements_raw)
        entrypoint = ensure_within_directory(app_dir / (entrypoint_raw or "app.py"), app_dir)
        icon = expand_path(icon_raw, app_dir) if Path(icon_raw).is_absolute() else (ensure_within_directory(app_dir / icon_raw, app_dir) if icon_raw else _default_icon_path())
        requirements = expand_path(requirements_raw, app_dir) if Path(requirements_raw).is_absolute() else (ensure_within_directory(app_dir / requirements_raw, app_dir) if requirements_raw else None)
        wheelhouse = ensure_within_directory(app_dir / wheelhouse_raw, app_dir)

    if direct and entrypoint.suffix.lower() != ".py":
        raise ManifestValidationError(f"Entrypoint must be a .py file: {entrypoint}")
    if not entrypoint.is_file():
        raise ManifestValidationError(f"Entrypoint does not exist: {entrypoint}")
    if not icon.is_file():
        if _default_icon_path().is_file():
            icon = _default_icon_path()
        else:
            raise ManifestValidationError(f"Icon does not exist: {icon}")
    if requirements is not None and not requirements.is_file():
        requirements = None
    if requirements is None:
        for candidate in (app_dir / "requirements.txt", app_dir / "requirement.txt"):
            if candidate.is_file():
                requirements = candidate.resolve()
                break
    if requirements is None:
        requirements = _infer_requirements(entrypoint)
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
        archived=bool(data.get("archived", False)),
    )


def _discover_from_registry(apps_directory: Path, include_disabled: bool) -> list[ApplicationManifest]:
    registry_path = apps_directory / "apps.json"
    registry = read_json(registry_path)
    schema_version = int(registry.get("schema_version", SUPPORTED_SCHEMA_VERSION))
    if schema_version not in SUPPORTED_REGISTRY_SCHEMA_VERSIONS:
        raise ManifestValidationError("Unsupported app registry schema version")
    defaults = registry.get("defaults", {})
    if not isinstance(defaults, dict) or not isinstance(registry.get("applications", []), list):
        raise ManifestValidationError("Registry defaults and applications must have valid types")
    policies = registry.get("policies", {}) if schema_version == 2 else {}
    if schema_version == 2:
        unknown = set(registry) - _V2_REGISTRY_KEYS
        if unknown:
            raise ManifestValidationError(f"Unknown v2 registry fields: {', '.join(sorted(unknown))}")
        if not isinstance(policies, dict):
            raise ManifestValidationError("Registry policies must be an object")
    discovered: list[ApplicationManifest] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_orders: set[int] = set()
    for app_data in registry.get("applications", []):
        try:
            if not isinstance(app_data, dict):
                raise ManifestValidationError("Application entries must be objects")
            if schema_version == 2:
                app_data = _normalize_v2_entry(apps_directory, defaults, app_data, policies)
            app = _manifest_from_registry_entry(apps_directory, defaults, app_data)
            if app.id in seen_ids:
                raise ManifestValidationError(f"Duplicate application ID: {app.id}")
            normalized_path = str(app.entrypoint.resolve()).casefold()
            if schema_version == 2 and normalized_path in seen_paths:
                raise ManifestValidationError(f"Duplicate application entrypoint: {app.entrypoint}")
            if schema_version == 2 and app.display_order in seen_orders:
                raise ManifestValidationError(f"Duplicate display order: {app.display_order}")
            seen_ids.add(app.id)
            seen_paths.add(normalized_path)
            seen_orders.add(app.display_order)
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
