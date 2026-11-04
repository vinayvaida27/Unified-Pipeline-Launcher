"""Local cache and platform state management."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .constants import STATE_SCHEMA_VERSION
from .models import ApplicationManifest
from .path_utils import atomic_write_json, read_json


class LocalCacheManager:
    """Manages local cache folders and state files."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.environments_dir = base_dir / "environments"
        self.apps_dir = base_dir / "apps"
        self.runtime_dir = base_dir / "runtime"
        self.logs_dir = base_dir / "logs"
        self.state_dir = base_dir / "state"
        self.staging_dir = base_dir / "staging"

    def ensure_directories(self) -> None:
        """Create expected local cache directories."""

        for path in (
            self.base_dir,
            self.apps_dir,
            self.runtime_dir,
            self.environments_dir,
            self.logs_dir,
            self.state_dir,
            self.staging_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def sync_runtime_to_local_cache(self, runtime_python: Path) -> Path:
        """Copy the bundled runtime into the per-user local cache.

        Network shares are a good distribution point, but the Python runtime
        should execute from local disk. This returns the cached python.exe path.
        """

        runtime_python = runtime_python.resolve()
        source_runtime_dir = runtime_python.parent
        try:
            runtime_python.relative_to(self.runtime_dir.resolve())
            return runtime_python
        except ValueError:
            pass

        fingerprint = self._fingerprint_directory_metadata(source_runtime_dir)
        cached_runtime_dir = self.runtime_dir / "current"
        cached_python = cached_runtime_dir / runtime_python.name
        marker_path = cached_runtime_dir / ".runtime_cache_ready.json"
        if not self._cache_marker_matches(marker_path, fingerprint):
            cached_runtime_dir.parent.mkdir(parents=True, exist_ok=True)
            temp_dir = cached_runtime_dir.parent / ".current.staging"
            self._force_rmtree(temp_dir)
            self._force_rmtree(cached_runtime_dir)
            shutil.copytree(source_runtime_dir, temp_dir, ignore=self._copy_ignore)
            self._safe_replace(temp_dir, cached_runtime_dir)
            atomic_write_json(
                marker_path,
                {
                    "source_path": str(source_runtime_dir),
                    "source_fingerprint": fingerprint,
                    "cached_python": str(cached_python),
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        return cached_python.resolve()

    def sync_apps_to_local_cache(self, apps: list[ApplicationManifest]) -> list[ApplicationManifest]:
        """Copy app source folders into the per-user local cache.

        This lets a published launcher live on a network drive while Streamlit
        source code executes from local disk for reliability and speed.
        """

        return [self.sync_app_to_local_cache(app) for app in apps]

    def sync_app_to_local_cache(self, app: ApplicationManifest) -> ApplicationManifest:
        """Copy one app to the local cache and return a manifest pointing there."""

        source_fingerprint = self._fingerprint_directory(app.app_dir)
        cached_app_dir = self.apps_dir / app.id / app.version
        marker_path = cached_app_dir / ".app_cache_ready.json"
        if not self._cache_marker_matches(marker_path, source_fingerprint):
            cached_app_dir.parent.mkdir(parents=True, exist_ok=True)
            temp_dir = cached_app_dir.parent / f".{cached_app_dir.name}.staging"
            self._force_rmtree(temp_dir)
            self._force_rmtree(cached_app_dir)
            shutil.copytree(app.app_dir, temp_dir, ignore=self._copy_ignore)
            self._safe_replace(temp_dir, cached_app_dir)
            atomic_write_json(
                marker_path,
                {
                    "app_id": app.id,
                    "app_version": app.version,
                    "source_path": str(app.app_dir),
                    "source_fingerprint": source_fingerprint,
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        return self._with_cached_paths(app, cached_app_dir)

    @property
    def state_path(self) -> Path:
        return self.state_dir / "platform_state.json"

    def load_state(self) -> dict:
        """Load platform state or return an empty state."""

        if not self.state_path.exists():
            return {"schema_version": STATE_SCHEMA_VERSION, "active_platform_version": "1.0.0", "applications": {}}
        return read_json(self.state_path)

    def update_app_state(self, app_id: str, installed_version: str, last_exit_code: int | None = None) -> None:
        """Atomically update one application's state."""

        state = self.load_state()
        apps = state.setdefault("applications", {})
        entry = apps.setdefault(app_id, {})
        entry["installed_version"] = installed_version
        entry["last_started_at"] = datetime.now(timezone.utc).isoformat()
        if last_exit_code is not None:
            entry["last_exit_code"] = last_exit_code
        atomic_write_json(self.state_path, state)

    @staticmethod
    def _force_rmtree(path: Path, attempts: int = 5) -> None:
        """Delete a directory tree on Windows even with read-only or briefly-locked files.

        CPython runtime files (e.g. from the NuGet package) are often read-only,
        which makes a plain shutil.rmtree fail with "directory not empty"; and
        antivirus/indexer handles can lock files transiently. This clears the
        read-only bit on error and retries with a short backoff.
        """

        if not path.exists():
            return

        def _on_error(func, target, _exc_info):
            try:
                os.chmod(target, stat.S_IWRITE)
                func(target)
            except OSError:
                pass

        for attempt in range(attempts):
            try:
                shutil.rmtree(path, onerror=_on_error)
            except OSError:
                pass
            if not path.exists():
                return
            time.sleep(0.3 * (attempt + 1))
        # Last try; let any final error surface with a clear message.
        if path.exists():
            shutil.rmtree(path, onerror=_on_error)

    @staticmethod
    def _safe_replace(source: Path, destination: Path, attempts: int = 5) -> None:
        """Atomically move a staged directory into place, retrying past transient locks."""

        for attempt in range(attempts):
            try:
                os.replace(source, destination)
                return
            except OSError:
                if attempt == attempts - 1:
                    raise
                time.sleep(0.3 * (attempt + 1))

    @staticmethod
    def _copy_ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {"__pycache__", ".pytest_cache", ".mypy_cache", ".streamlit"}
        return {name for name in names if name in ignored or name.endswith((".pyc", ".pyo", ".log"))}

    @staticmethod
    def _cache_marker_matches(marker_path: Path, fingerprint: str) -> bool:
        if not marker_path.exists():
            return False
        try:
            marker = read_json(marker_path)
        except (OSError, ValueError):
            return False
        return marker.get("source_fingerprint") == fingerprint

    @staticmethod
    def _fingerprint_directory(directory: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.name == ".app_cache_ready.json":
                continue
            if any(part in {"__pycache__", ".pytest_cache", ".mypy_cache", ".streamlit"} for part in path.parts):
                continue
            relative = path.relative_to(directory).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

    # Files at or below this size are content-hashed so that a same-size edit
    # made within the filesystem mtime resolution is still detected. Larger
    # files (big DLLs) fall back to size + mtime to keep startup fast.
    _CONTENT_HASH_MAX_BYTES = 8 * 1024 * 1024

    @staticmethod
    def _fingerprint_directory_metadata(directory: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.name.endswith(".log"):
                continue
            if any(part in {"__pycache__", ".pytest_cache", ".mypy_cache"} for part in path.parts):
                continue
            stat = path.stat()
            relative = path.relative_to(directory).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
            if stat.st_size <= LocalCacheManager._CONTENT_HASH_MAX_BYTES:
                digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _with_cached_paths(app: ApplicationManifest, cached_app_dir: Path) -> ApplicationManifest:
        entrypoint_relative = app.entrypoint.relative_to(app.app_dir)
        icon_relative = app.icon.relative_to(app.app_dir)
        requirements_relative = app.requirements.relative_to(app.app_dir)
        wheelhouse_relative = app.wheelhouse.relative_to(app.app_dir)
        return replace(
            app,
            app_dir=cached_app_dir.resolve(),
            entrypoint=(cached_app_dir / entrypoint_relative).resolve(),
            icon=(cached_app_dir / icon_relative).resolve(),
            requirements=(cached_app_dir / requirements_relative).resolve(),
            wheelhouse=(cached_app_dir / wheelhouse_relative).resolve(),
        )
