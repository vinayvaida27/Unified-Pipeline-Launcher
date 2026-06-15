"""Virtual environment management for applications."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import DependencyInstallationError, EnvironmentCreationError, RuntimeNotFoundError, RuntimeValidationError
from .models import ApplicationManifest, EnvironmentState, PlatformConfig
from .path_utils import atomic_write_json


class RuntimeResolver:
    """Resolves and validates the Python runtime."""

    def __init__(self, config: PlatformConfig, development_mode: bool = False) -> None:
        self.config = config
        self.development_mode = development_mode

    def resolve(self, validate: bool = True) -> Path:
        """Resolve the runtime path according to production/development rules."""

        runtime_python = self.config.paths.runtime_python
        if runtime_python.exists():
            if validate:
                self.validate(runtime_python)
            return runtime_python
        if self.development_mode and self.config.runtime.allow_development_interpreter_fallback:
            fallback = Path(sys.executable)
            if validate:
                self.validate(fallback)
            return fallback
        raise RuntimeNotFoundError(f"Bundled runtime is missing: {runtime_python}")

    def validate(self, python_path: Path) -> None:
        """Validate Python version, venv, pip, SSL, and subprocess support."""

        if not python_path.exists():
            raise RuntimeNotFoundError(str(python_path))
        script = "import ssl, subprocess, venv, pip, sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
        result = subprocess.run([str(python_path), "-c", script], capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            raise RuntimeValidationError(result.stderr.strip() or "Runtime validation failed")
        major, minor, *_ = result.stdout.strip().split(".")
        if (int(major), int(minor)) < (3, 11) or (int(major), int(minor)) >= (3, 13):
            raise RuntimeValidationError(f"Unsupported Python version: {result.stdout.strip()}")


def scrubbed_environment() -> dict[str, str]:
    """Return a child-process environment without system-Python contamination."""

    env = os.environ.copy()
    for variable in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE"):
        env.pop(variable, None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


class EnvironmentManager:
    """Creates and validates per-app/per-version virtual environments."""

    VENV_TIMEOUT_SECONDS = 300
    PIP_TIMEOUT_SECONDS = 1800

    def __init__(self, config: PlatformConfig, runtime_python: Path) -> None:
        self.config = config
        self.runtime_python = runtime_python
        self.environments_dir = config.paths.local_cache_directory / "environments"
        self.logs_dir = config.paths.local_cache_directory / "logs"

    def environment_path_for(self, app: ApplicationManifest) -> Path:
        """Return deterministic environment path for an app version."""
        return self.environments_dir / app.id / app.version

    def venv_python_for(self, environment_path: Path) -> Path:
        """Return the Python executable path inside a Windows venv."""
        if sys.platform == "win32":
            return environment_path / "Scripts" / "python.exe"
        return environment_path / "bin" / "python"

    def marker_path_for(self, environment_path: Path) -> Path:
        return environment_path / ".environment_ready.json"

    def requirements_hash(self, requirements_path: Path) -> str:
        """Return SHA-256 for requirements file."""
        digest = hashlib.sha256()
        digest.update(requirements_path.read_bytes())
        return digest.hexdigest()

    def runtime_fingerprint(self) -> str:
        """Identify the runtime build so venvs rebuild after runtime updates."""
        try:
            stat = self.runtime_python.stat()
            return f"{self.runtime_python.resolve().as_posix()}|{stat.st_size}|{stat.st_mtime_ns}"
        except OSError:
            return str(self.runtime_python)

    def is_ready(self, app: ApplicationManifest) -> bool:
        """Return whether an environment marker matches current inputs."""
        env_path = self.environment_path_for(app)
        marker = self.marker_path_for(env_path)
        python_path = self.venv_python_for(env_path)
        if not marker.exists() or not python_path.exists():
            return False
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        return (
            data.get("app_id") == app.id
            and data.get("app_version") == app.version
            and data.get("requirements_sha256") == self.requirements_hash(app.requirements)
            and data.get("runtime_fingerprint") == self.runtime_fingerprint()
        )

    def pip_install_command(self, app: ApplicationManifest, venv_python: Path) -> list[str]:
        """Build the dependency installation command."""
        command = [str(venv_python), "-m", "pip", "install"]
        if self.config.runtime.offline_install_preferred and app.wheelhouse.exists() and any(app.wheelhouse.iterdir()):
            command.extend(["--no-index", "--find-links", str(app.wheelhouse)])
        command.extend(["-r", str(app.requirements)])
        return command

    def _run_logged(self, command: list[str], log_handle, timeout_seconds: int, failure_message: str, error_cls) -> None:
        """Run a command streaming output to the app log, with a timeout."""
        log_handle.write(f"\n{datetime.now(timezone.utc).isoformat()} Running: {' '.join(command)}\n")
        log_handle.flush()
        try:
            result = subprocess.run(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=scrubbed_environment(),
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise error_cls(f"{failure_message}: timed out after {timeout_seconds} seconds") from exc
        if result.returncode != 0:
            raise error_cls(f"{failure_message} (exit code {result.returncode}). Open the application log for details.")

    def shared_runtime_state(self, app: ApplicationManifest) -> EnvironmentState:
        """Return an EnvironmentState pointing directly to the bundled runtime.

        Used when create_virtual_environments is disabled.  The admin runs
        scripts/prepare_shared_runtime.ps1 once to pre-install all packages.
        No venv creation, no pip install -- startup is instant for every user.
        """
        marker_path = self.runtime_python.parent / ".shared_runtime_ready.json"
        return EnvironmentState(
            app.id, app.version, self.runtime_python.parent, self.runtime_python, True, marker_path
        )

    def ensure_environment(self, app: ApplicationManifest, progress=None) -> EnvironmentState:
        """Create or reuse an app environment.

        Fast path: when create_virtual_environments is False the shared bundled
        runtime is returned immediately.  No venv, no pip install, zero wait.

        Normal path: per-app/per-version venvs are created on first launch and
        reused on all subsequent launches (existing behaviour).
        """
        # Fast path: shared runtime mode.
        if not self.config.runtime.create_virtual_environments:
            if progress:
                progress("Using shared runtime")
            return self.shared_runtime_state(app)

        # Normal path: per-app isolated virtual environment.
        env_path = self.environment_path_for(app)
        venv_python = self.venv_python_for(env_path)
        marker_path = self.marker_path_for(env_path)
        if progress:
            progress("Checking environment")
        if self.is_ready(app):
            return EnvironmentState(app.id, app.version, env_path, venv_python, True, marker_path)
        env_path.parent.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.logs_dir / f"{app.id}.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            ts = datetime.now(timezone.utc).isoformat()
            log_handle.write(f"{ts} Preparing environment for {app.name} {app.version}\n")
            if progress:
                progress("Creating virtual environment")
            self._run_logged(
                [str(self.runtime_python), "-m", "venv", str(env_path)],
                log_handle,
                self.VENV_TIMEOUT_SECONDS,
                "Virtual environment creation failed",
                EnvironmentCreationError,
            )
            if progress:
                progress("Installing dependencies")
            self._run_logged(
                self.pip_install_command(app, venv_python),
                log_handle,
                self.PIP_TIMEOUT_SECONDS,
                "Dependency installation failed",
                DependencyInstallationError,
            )
            if progress:
                progress("Validating environment")
            self._run_logged(
                [str(venv_python), "-c", "import streamlit"],
                log_handle,
                self.VENV_TIMEOUT_SECONDS,
                "Streamlit validation import failed",
                DependencyInstallationError,
            )
        py_ver = subprocess.check_output(
            [str(venv_python), "--version"], text=True, env=scrubbed_environment()
        ).strip()
        atomic_write_json(
            marker_path,
            {
                "app_id": app.id,
                "app_version": app.version,
                "python_version": py_ver,
                "requirements_sha256": self.requirements_hash(app.requirements),
                "runtime_fingerprint": self.runtime_fingerprint(),
                "installed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return EnvironmentState(app.id, app.version, env_path, venv_python, True, marker_path)
