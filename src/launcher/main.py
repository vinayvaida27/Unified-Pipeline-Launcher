"""Launcher application entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .app_discovery import discover_apps
from .config_loader import load_platform_config
from .environment_manager import EnvironmentManager, RuntimeResolver
from .exceptions import LauncherError, RuntimeNotFoundError
from .local_cache import LocalCacheManager
from .logging_setup import configure_logging
from .path_utils import is_remote_path
from .process_manager import ProcessManager
from .runtime_downloader import RuntimeDownloader

LOG = logging.getLogger(__name__)
WINDOWS_APP_ID = "UnifiedPipelineLauncher.Desktop"


def _set_windows_app_id() -> None:
    """Give Windows a stable identity for taskbar grouping and icons."""

    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        LOG.debug("Could not set the Windows application ID", exc_info=True)


def should_sync_to_local_cache(config) -> bool:
    """Use local execution when configured or when source files are remote."""

    return (
        config.runtime.sync_to_local_cache
        or is_remote_path(config.paths.runtime_python)
        or is_remote_path(config.paths.apps_directory)
    )


def installation_root() -> Path:
    """Return the launcher installation directory.

    Resolved from the frozen executable location (PyInstaller) or the
    repository root in development, never from the working directory, so
    shortcuts with a different "Start in" folder still work.
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_config_path(raw: str | None) -> Path:
    """Resolve the configuration path independent of the working directory."""

    if raw:
        candidate = Path(raw).expanduser()
        if candidate.is_absolute():
            return candidate
        cwd_candidate = Path.cwd() / candidate
        if cwd_candidate.exists():
            return cwd_candidate
        return installation_root() / candidate
    return installation_root() / "config" / "launcher_config.json"


def _download_runtime_with_dialog(config, qt_app):
    """Download the pinned official runtime while showing progress."""

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QProgressDialog

    dialog = QProgressDialog("Preparing Python runtime...", "", 0, 0)
    dialog.setCancelButton(None)
    dialog.setWindowTitle(config.platform_name)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setMinimumDuration(0)
    dialog.show()

    def progress(message: str) -> None:
        dialog.setLabelText(message)
        qt_app.processEvents()

    try:
        return RuntimeDownloader(config).ensure_runtime(progress=progress)
    finally:
        dialog.close()


def main(argv: list[str] | None = None) -> int:
    """Run the desktop launcher."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args(argv)

    _set_windows_app_id()

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox

    qt_app = QApplication(sys.argv[:1])
    icon = QIcon(str(installation_root() / "assets" / "launcher" / "launcher.png"))
    if not icon.isNull():
        qt_app.setWindowIcon(icon)

    try:
        config = load_platform_config(resolve_config_path(args.config))
        cache = LocalCacheManager(config.paths.local_cache_directory)
        cache.ensure_directories()
        configure_logging(config.paths.local_cache_directory, config.logging)
        process_manager = ProcessManager(cache.logs_dir)
        process_manager.cleanup_stale_processes()
        sync_to_local_cache = should_sync_to_local_cache(config)

        if sync_to_local_cache:
            apps = cache.sync_apps_to_local_cache(discover_apps(config.paths.apps_directory))
        else:
            apps = discover_apps(config.paths.apps_directory)

        runtime_resolver = RuntimeResolver(config, development_mode=args.development)
        try:
            runtime_python = runtime_resolver.resolve(validate=args.development)
        except RuntimeNotFoundError:
            if args.development or not config.runtime.download.enabled:
                raise
            LOG.info("Bundled runtime missing; downloading pinned official Python runtime")
            runtime_python = _download_runtime_with_dialog(config, qt_app)
        if not args.development and sync_to_local_cache:
            runtime_python = cache.sync_runtime_to_local_cache(runtime_python)
            if cache.runtime_cache_refreshed:
                runtime_resolver.validate(runtime_python)
    except LauncherError as exc:
        LOG.exception("Launcher startup failed")
        QMessageBox.critical(
            None,
            "Launcher could not start",
            f"{exc}\n\nPlease contact your administrator if the problem persists.",
        )
        return 1

    env_manager = EnvironmentManager(config, runtime_python)

    from .ui.main_window import MainWindow

    window = MainWindow(config, apps, env_manager, process_manager)
    window.show()
    result = qt_app.exec()
    if config.launcher.stop_apps_on_exit:
        process_manager.stop_all()
    LOG.info("Launcher exited with code %s", result)
    return int(result)
