"""Typed models used by the launcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from subprocess import Popen
from typing import Any


class ApplicationStatus(str, Enum):
    """Runtime status for an application card."""

    STOPPED = "Stopped"
    STARTING = "Starting"
    RUNNING = "Running"
    STOPPING = "Stopping"
    FAILED = "Failed"
    DISABLED = "Disabled"


@dataclass(frozen=True)
class WindowConfig:
    width: int
    height: int
    minimum_width: int
    minimum_height: int


@dataclass(frozen=True)
class PathConfig:
    apps_directory: Path
    runtime_python: Path
    local_cache_directory: Path
    network_release_directory: Path | None = None
    shared_data_directory: Path | None = None
    user_output_directory: Path | None = None


@dataclass(frozen=True)
class RuntimeDownloadConfig:
    """Pinned official CPython download used when no runtime is bundled."""

    enabled: bool = False
    version: str = ""
    url: str = ""
    sha256: str = ""


@dataclass(frozen=True)
class RuntimeConfig:
    allow_development_interpreter_fallback: bool
    create_virtual_environments: bool
    environment_strategy: str
    offline_install_preferred: bool
    sync_to_local_cache: bool = True
    download: RuntimeDownloadConfig = field(default_factory=RuntimeDownloadConfig)


@dataclass(frozen=True)
class UpdateConfig:
    enabled: bool
    check_on_startup: bool
    retain_previous_versions: int
    verify_sha256: bool


@dataclass(frozen=True)
class LauncherBehaviorConfig:
    open_browser_after_start: bool
    minimize_to_tray: bool
    stop_apps_on_exit: bool
    maximum_parallel_startups: int


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    maximum_file_size_mb: int
    backup_count: int


@dataclass(frozen=True)
class PlatformConfig:
    schema_version: int
    platform_name: str
    organization_name: str
    window: WindowConfig
    paths: PathConfig
    runtime: RuntimeConfig
    updates: UpdateConfig
    launcher: LauncherBehaviorConfig
    logging: LoggingConfig
    source_path: Path


@dataclass(frozen=True)
class LaunchSettings:
    address: str
    port: str
    headless: bool
    file_watcher_type: str
    gather_usage_stats: bool
    startup_timeout_seconds: int


@dataclass(frozen=True)
class ApplicationManifest:
    schema_version: int
    id: str
    name: str
    version: str
    description: str
    category: str
    type: str
    entrypoint: Path
    icon: Path
    requirements: Path
    wheelhouse: Path
    python_version: str
    enabled: bool
    display_order: int
    launch: LaunchSettings
    app_dir: Path


@dataclass
class ApplicationRuntimeState:
    app_id: str
    app_name: str
    app_version: str
    process: Popen[Any] | None
    process_id: int | None
    port: int | None
    url: str | None
    start_time: str | None
    log_path: Path | None
    status: ApplicationStatus
    environment_path: Path | None
    entrypoint_path: Path


@dataclass(frozen=True)
class EnvironmentState:
    app_id: str
    app_version: str
    environment_path: Path
    python_path: Path
    ready: bool
    marker_path: Path


@dataclass(frozen=True)
class ChecksumEntry:
    relative_path: str
    sha256: str


@dataclass(frozen=True)
class UpdateApplicationEntry:
    id: str
    version: str
    relative_path: str
    sha256_manifest: str


@dataclass(frozen=True)
class UpdateManifest:
    schema_version: int
    platform_version: str
    published_at: str
    applications: list[UpdateApplicationEntry] = field(default_factory=list)
