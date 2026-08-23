"""Streamlit process management."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import ApplicationStartError, ApplicationStopError
from .health_checker import HealthChecker
from .models import ApplicationManifest, ApplicationRuntimeState, ApplicationStatus, EnvironmentState
from .path_utils import atomic_write_json, read_json
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
            "--server.enableCORS",
            "true",
            "--server.enableXsrfProtection",
            "true",
        ]

    def start(self, app: ApplicationManifest, env: EnvironmentState) -> ApplicationRuntimeState:
        """Start an app, returning existing state when already running."""

        with self._lock:
            existing = self._running.get(app.id)
            if existing and existing.process and existing.process.poll() is None:
                return existing
            self._stop_stale_process(app.id)
            port = self.port_manager.get_available_port()
            log_path = self.logs_dir / f"{app.id}.log"
            command = self.build_command(app, env, port)
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
            env_vars = os.environ.copy()
            for variable in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE"):
                env_vars.pop(variable, None)
            env_vars["PYTHONNOUSERSITE"] = "1"
            try:
                with log_path.open("w", encoding="utf-8") as log_handle:
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
            self._write_runtime_marker(state, env.python_path)
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
                self._remove_runtime_marker(app_id)
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
            if HealthChecker._port_from_url(url) != state.port:
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
                tree_stopped = self._runtime_marker_matches_process(app_id, process.pid)
                tree_stopped = tree_stopped and self._terminate_process_tree(process.pid)
                if tree_stopped:
                    process.wait(timeout=5)
                else:
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
            self._remove_runtime_marker(app_id)

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

    def cleanup_stale_processes(self) -> None:
        """Stop identity-matched app processes left by a crashed launcher."""

        suffix = ".runtime.json"
        for marker_path in self.logs_dir.glob(f"*{suffix}"):
            self._stop_stale_process(marker_path.name[: -len(suffix)])

    def _runtime_marker_path(self, app_id: str) -> Path:
        return self.logs_dir / f"{app_id}.runtime.json"

    def _write_runtime_marker(self, state: ApplicationRuntimeState, python_path: Path) -> None:
        if state.process_id is None:
            return
        identity = self._process_identity(state.process_id)
        expected_executable = os.path.normcase(os.path.abspath(python_path))
        if identity is None or identity.get("executable") != expected_executable:
            return
        owner_identity = self._process_identity(os.getpid())
        atomic_write_json(
            self._runtime_marker_path(state.app_id),
            {
                "pid": state.process_id,
                "identity": identity,
                "entrypoint": str(state.entrypoint_path),
                "started_at": state.start_time,
                "owner_pid": os.getpid(),
                "owner_identity": owner_identity,
            },
        )

    def _stop_stale_process(self, app_id: str) -> None:
        marker_path = self._runtime_marker_path(app_id)
        if not marker_path.exists():
            return
        try:
            marker = read_json(marker_path)
            pid = int(marker["pid"])
            expected_identity = marker["identity"]
        except (KeyError, OSError, TypeError, ValueError):
            self._remove_runtime_marker(app_id)
            return
        try:
            owner_pid = int(marker["owner_pid"]) if marker.get("owner_pid") else None
        except (TypeError, ValueError):
            owner_pid = None
        owner_identity = marker.get("owner_identity")
        if owner_pid and owner_identity is not None and owner_identity == self._process_identity(owner_pid):
            raise ApplicationStartError(f"{app_id} is managed by another active launcher")
        actual_identity = self._process_identity(pid)
        if actual_identity is not None and actual_identity == expected_identity and not self._terminate_process_tree(pid):
            raise ApplicationStartError(f"A stale {app_id} process could not be stopped safely")
        self._remove_runtime_marker(app_id)

    def _remove_runtime_marker(self, app_id: str) -> None:
        try:
            self._runtime_marker_path(app_id).unlink(missing_ok=True)
        except OSError:
            pass

    def _runtime_marker_matches_process(self, app_id: str, pid: int) -> bool:
        try:
            marker = read_json(self._runtime_marker_path(app_id))
            return int(marker["pid"]) == pid and marker["identity"] == self._process_identity(pid)
        except (KeyError, OSError, TypeError, ValueError):
            return False

    @staticmethod
    def _process_identity(pid: int) -> dict[str, int | str] | None:
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetProcessTimes.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME),
            ]
            kernel32.QueryFullProcessImageNameW.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.LPWSTR,
                ctypes.POINTER(wintypes.DWORD),
            ]
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return None
            try:
                created = wintypes.FILETIME()
                exited = wintypes.FILETIME()
                kernel = wintypes.FILETIME()
                user = wintypes.FILETIME()
                if not kernel32.GetProcessTimes(handle, created, exited, kernel, user):
                    return None
                buffer = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(buffer))
                if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    return None
                created_at = (created.dwHighDateTime << 32) | created.dwLowDateTime
                return {
                    "created_at": created_at,
                    "executable": os.path.normcase(os.path.abspath(buffer.value)),
                }
            finally:
                kernel32.CloseHandle(handle)
        except (AttributeError, OSError, ValueError):
            return None

    def _terminate_process_tree(self, pid: int) -> bool:
        if sys.platform != "win32":
            return False
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
                creationflags=creationflags,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0 or self._process_identity(pid) is None
