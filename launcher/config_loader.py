"""Platform configuration loader."""

from __future__ import annotations

from pathlib import Path

from .constants import SUPPORTED_SCHEMA_VERSION
from .exceptions import ConfigurationError
from .models import (
    LauncherBehaviorConfig,
    LoggingConfig,
    PathConfig,
    PlatformConfig,
    RuntimeConfig,
    RuntimeDownloadConfig,
    UpdateConfig,
    WindowConfig,
)
from .path_utils import expand_path, read_json


def _require(data: dict, key: str):
    if key not in data:
        raise ConfigurationError(f"Missing required configuration field: {key}")
    return data[key]


def _optional_path(value: str, base_dir: Path) -> Path | None:
    if not value:
        return None
    return expand_path(value, base_dir)


def load_platform_config(config_path: Path) -> PlatformConfig:
    """Load and validate launcher configuration."""

    data = read_json(config_path)
    if data.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ConfigurationError("Unsupported launcher configuration schema version")
    base_dir = config_path.resolve().parent
    paths = _require(data, "paths")
    runtime = _require(data, "runtime")
    updates = _require(data, "updates")
    launcher = _require(data, "launcher")
    logging_cfg = _require(data, "logging")
    window = _require(data, "window")

    return PlatformConfig(
        schema_version=data["schema_version"],
        platform_name=str(_require(data, "platform_name")),
        organization_name=str(_require(data, "organization_name")),
        window=WindowConfig(
            width=int(_require(window, "width")),
            height=int(_require(window, "height")),
            minimum_width=int(_require(window, "minimum_width")),
            minimum_height=int(_require(window, "minimum_height")),
        ),
        paths=PathConfig(
            apps_directory=expand_path(str(_require(paths, "apps_directory")), base_dir),
            runtime_python=expand_path(str(_require(paths, "runtime_python")), base_dir),
            local_cache_directory=expand_path(str(_require(paths, "local_cache_directory")), base_dir),
            network_release_directory=_optional_path(str(paths.get("network_release_directory", "")), base_dir),
            shared_data_directory=_optional_path(str(paths.get("shared_data_directory", "")), base_dir),
            user_output_directory=_optional_path(str(paths.get("user_output_directory", "")), base_dir),
        ),
        runtime=RuntimeConfig(
            allow_development_interpreter_fallback=bool(_require(runtime, "allow_development_interpreter_fallback")),
            create_virtual_environments=bool(_require(runtime, "create_virtual_environments")),
            environment_strategy=str(_require(runtime, "environment_strategy")),
            offline_install_preferred=bool(_require(runtime, "offline_install_preferred")),
            sync_to_local_cache=bool(runtime.get("sync_to_local_cache", True)),
            download=RuntimeDownloadConfig(
                enabled=bool(runtime.get("download", {}).get("enabled", False)),
                version=str(runtime.get("download", {}).get("version", "")),
                url=str(runtime.get("download", {}).get("url", "")),
                sha256=str(runtime.get("download", {}).get("sha256", "")),
            ),
        ),
        updates=UpdateConfig(
            enabled=bool(_require(updates, "enabled")),
            check_on_startup=bool(_require(updates, "check_on_startup")),
            retain_previous_versions=int(_require(updates, "retain_previous_versions")),
            verify_sha256=bool(_require(updates, "verify_sha256")),
        ),
        launcher=LauncherBehaviorConfig(
            open_browser_after_start=bool(_require(launcher, "open_browser_after_start")),
            minimize_to_tray=bool(_require(launcher, "minimize_to_tray")),
            stop_apps_on_exit=bool(_require(launcher, "stop_apps_on_exit")),
            maximum_parallel_startups=int(_require(launcher, "maximum_parallel_startups")),
        ),
        logging=LoggingConfig(
            level=str(_require(logging_cfg, "level")),
            maximum_file_size_mb=int(_require(logging_cfg, "maximum_file_size_mb")),
            backup_count=int(_require(logging_cfg, "backup_count")),
        ),
        source_path=config_path.resolve(),
    )
