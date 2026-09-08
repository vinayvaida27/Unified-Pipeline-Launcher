"""Launcher application entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .app_discovery import discover_apps
from .config_loader import load_platform_config
from .environment_manager import EnvironmentManager, RuntimeResolver
from .exceptions import LauncherError, RuntimeNotFoundError
from .local_cache import LocalCacheManager
from .logging_setup import configure_logging
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
    """Use local caching only when it is explicitly enabled in configuration.

    A mapped drive or UNC source is a valid deployment location.  It must not
    silently trigger a full runtime/app copy before the launcher window appears.
    """

    return bool(config.runtime.sync_to_local_cache)


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


def _busy_dialog(config, qt_app, message: str):
    """Show an indeterminate progress dialog before an expensive operation."""

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QProgressDialog

    dialog = QProgressDialog(message, "", 0, 0)
    dialog.setCancelButton(None)
    dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
    dialog.setWindowTitle(config.platform_name)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setMinimumDuration(0)
    dialog.show()
    qt_app.processEvents()
    return dialog


def _run_with_progress(config, qt_app, message, operation):
    """Run startup I/O in the existing worker pool while Qt remains responsive."""

    from PySide6.QtCore import QEventLoop, QThreadPool, Qt
    from .ui.workers import Worker

    dialog = _busy_dialog(config, qt_app, message)
    loop = QEventLoop()
    result, errors, domain_errors = [], [], []

    def perform(progress):
        try:
            return operation(progress=progress)
        except LauncherError as exc:
            domain_errors.append(exc)
            raise

    worker = Worker(perform)
    worker.signals.progress.connect(dialog.setLabelText, Qt.ConnectionType.QueuedConnection)
    worker.signals.finished.connect(result.append, Qt.ConnectionType.QueuedConnection)
    worker.signals.finished.connect(loop.quit, Qt.ConnectionType.QueuedConnection)
    worker.signals.failed.connect(lambda message, trace: errors.append((message, trace)), Qt.ConnectionType.QueuedConnection)
    worker.signals.failed.connect(loop.quit, Qt.ConnectionType.QueuedConnection)
    started = time.perf_counter()
    QThreadPool.globalInstance().start(worker)

    try:
        loop.exec()
    finally:
        dialog.close()
        LOG.info("Startup operation %s took %.3fs", message, time.perf_counter() - started)
    if errors:
        LOG.error("Startup worker failed: %s", errors[0][1])
        if domain_errors:
            raise domain_errors[0]
        raise LauncherError(errors[0][0])
    return result[0]


def _download_runtime_with_dialog(config, qt_app):
    runtime_python = _run_with_progress(config, qt_app, "Preparing Python runtime...", RuntimeDownloader(config).ensure_runtime)
    _run_with_progress(config, qt_app, "Validating downloaded runtime...",
                       lambda progress: RuntimeResolver(config).validate(runtime_python))
    return runtime_python


def main(argv: list[str] | None = None) -> int:
    """Run the desktop launcher."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--development", action="store_true")
    parser.add_argument(
        "--no-local-cache",
        action="store_true",
        help="Run directly from the configured runtime/apps without copying them to the local cache.",
    )
    args = parser.parse_args(argv)

    started = time.perf_counter()
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

        sync_to_local_cache = should_sync_to_local_cache(config) and not args.no_local_cache
        discovery_started = time.perf_counter()
        source_apps = discover_apps(config.paths.apps_directory)
        LOG.info("App discovery took %.3fs", time.perf_counter() - discovery_started)
        if sync_to_local_cache:
            apps = _run_with_progress(config, qt_app, "Updating local application cache...",
                                      lambda progress: cache.sync_apps_to_local_cache(source_apps))
        else:
            apps = source_apps

        runtime_resolver = RuntimeResolver(config, development_mode=args.development)
        try:
            validation_started = time.perf_counter()
            runtime_python = _run_with_progress(config, qt_app, "Checking launcher runtime...",
                                                lambda progress: runtime_resolver.resolve(validate=True))
            LOG.info("Runtime validation took %.3fs", time.perf_counter() - validation_started)
        except RuntimeNotFoundError:
            if args.development or not config.runtime.download.enabled:
                raise
            LOG.info("Bundled runtime missing; downloading pinned official Python runtime")
            runtime_python = _download_runtime_with_dialog(config, qt_app)

        if not args.development and sync_to_local_cache:
            runtime_python = _run_with_progress(config, qt_app, "Updating local launcher runtime...",
                                                lambda progress: cache.sync_runtime_to_local_cache(runtime_python))
            if cache.runtime_cache_refreshed:
                _run_with_progress(config, qt_app, "Validating local runtime...",
                                   lambda progress: runtime_resolver.validate(runtime_python))
        env_manager = EnvironmentManager(config, runtime_python)
        from .ui.main_window import MainWindow
        window = MainWindow(config, apps, env_manager, process_manager)
        window.show()
        LOG.info("First window shown after %.3fs", time.perf_counter() - started)
    except Exception as exc:
        LOG.exception("Launcher startup failed")
        QMessageBox.critical(
            None,
            "Launcher could not start",
            f"{exc}\n\nPlease contact your administrator if the problem persists.",
        )
        return 1
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, lambda: LOG.info("First event-loop turn after %.3fs", time.perf_counter() - started))
    try:
        result = qt_app.exec()
    finally:
        if config.launcher.stop_apps_on_exit:
            process_manager.stop_all()
    LOG.info("Launcher exited with code %s", result)
    return int(result)
