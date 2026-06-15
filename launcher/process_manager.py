"""Streamlit process management."""

from __future__ import annotations

import os
from urllib.parse import urlparse
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import ApplicationStartError, ApplicationStopError
from .health_checker import HealthChecker
from .models import ApplicationManifest, ApplicationRuntimeState, ApplicationStatus, EnvironmentState
from .port_manager import PortManager


class ProcessManager:
    """Central registry and controller for launched applications."""

    def __init__(self, logs_dir: Path, port_manager: PortManager | None = None, health_checker: HealthChecker | None = None) -> None:
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.port_manager = port_manager or PortManager()
        self.health_checker = health_checker or HealthChecker()
        self._lock = threading.RLock()
        self._running: dict[str, ApplicationRuntimeState] = {}

    def build_command(self, app: ApplicationManifest, env: EnvironmentState, port: int) -> list[str]:
        """Build the Streamlit launch command as an argument list."""

        return [
            str(env.python_path),
            "-m",
            "streamlit",
            "run",
            str(app.entrypoint),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            app.launch.file_watcher_type,
        ]

    def start(self, app: ApplicationManifest, env: EnvironmentState) -> ApplicationRuntimeState:
        """Start an app, returning existing state when already running."""

        with self._lock:
            existing = self._running.get(app.id)
            if existing and existing.process and existing.process.poll() is None:
                return existing
            port = self.port_manager.get_available_port()
            log_path = self.logs_dir / f"{app.id}.log"
            command = self.build_command(app, env, port)
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
            env_vars = os.environ.copy()
            for variable in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE"):
                env_vars.pop(variable, None)
            env_vars["PYTHONNOUSERSITE"] = "1"
            try:
                log_handle = log_path.open("w", encoding="utf-8")
                log_handle.write(f"{datetime.now(timezone.utc).isoformat()} Launcher starting {app.name} {app.version}\n")
                log_handle.write(f"Command: {' '.join(command)}\n\n")
                log_handle.flush()
                process = subprocess.Popen(
                    command,
                    cwd=str(app.app_dir),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    shell=False,
                    env=env_vars,
                    creationflags=creationflags,
                )
            except OSError as exc:
                self.port_manager.release(port)
                raise ApplicationStartError(str(exc)) from exc
            state = ApplicationRuntimeState(
                app_id=app.id,
                app_name=app.name,
                app_version=app.version,
                process=process,
                process_id=process.pid,
                port=port,
                url=None,
                start_time=datetime.now(timezone.utc).isoformat(),
                log_path=log_path,
                status=ApplicationStatus.STARTING,
                environment_path=env.environment_path,
                entrypoint_path=app.entrypoint,
            )
            self._running[app.id] = state
        try:
            url = self.health_checker.wait_until_healthy(process, port, app.launch.startup_timeout_seconds, log_path)
        except Exception:
            self.stop(app.id)
            raise
        with self._lock:
            state.url = url
            state.status = ApplicationStatus.RUNNING
            return state

    def get(self, app_id: str) -> ApplicationRuntimeState | None:
        """Return tracked state for an app."""

        with self._lock:
            state = self._running.get(app_id)
            if state and state.process and state.process.poll() is not None:
                state.status = ApplicationStatus.FAILED
                self.port_manager.release(state.port)
                self._running.pop(app_id, None)
                return None
            return state

    def mark_running_from_url(self, app_id: str, url: str) -> ApplicationRuntimeState | None:
        """Mark a tracked app running when an external readiness signal has a URL."""

        with self._lock:
            state = self._running.get(app_id)
            if not state:
                return None
            if not state.process or state.process.poll() is not None:
                return None
            if urlparse(url).port != state.port:
                return None
            state.url = url
            state.status = ApplicationStatus.RUNNING
            return state

    def stop(self, app_id: str, timeout_seconds: float = 8) -> None:
        """Stop one running app."""

        with self._lock:
            state = self._running.get(app_id)
        if not state or not state.process:
            return
        process = state.process
        state.status = ApplicationStatus.STOPPING
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        except OSError as exc:
            raise ApplicationStopError(str(exc)) from exc
        finally:
            self.port_manager.release(state.port)
            with self._lock:
                self._running.pop(app_id, None)

    def restart(self, app: ApplicationManifest, env: EnvironmentState) -> ApplicationRuntimeState:
        """Restart an application."""

        self.stop(app.id)
        return self.start(app, env)

    def stop_all(self) -> None:
        """Stop all tracked applications."""

        for app_id in list(self._running):
            self.stop(app_id)

    def running_states(self) -> list[ApplicationRuntimeState]:
        """Return currently tracked running states."""

        with self._lock:
            return list(self._running.values())
