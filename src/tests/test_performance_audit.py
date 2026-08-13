from __future__ import annotations

import json
import os
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from launcher.app_discovery import discover_apps
from launcher.health_checker import HealthChecker
from launcher.models import EnvironmentState
from launcher.process_manager import ProcessManager


pytestmark = [pytest.mark.integration, pytest.mark.performance]


if os.environ.get("RUN_PERFORMANCE_AUDIT") != "1":
    pytest.skip("set RUN_PERFORMANCE_AUDIT=1 to run load and lifecycle measurements", allow_module_level=True)


def _environment(tmp_path: Path, app) -> EnvironmentState:
    python = Path(sys.executable)
    return EnvironmentState(app.id, app.version, python.parent, python, True, tmp_path / "ready.json")


def _process_tree_rss(psutil, state) -> tuple[int, int]:
    root = psutil.Process(state.process_id)
    tree = [root, *root.children(recursive=True)]
    return len(tree), sum(process.memory_info().rss for process in tree)


def test_launcher_window_one_app_and_two_app_startup(repo_root, config, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    psutil = pytest.importorskip("psutil")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from launcher.ui.main_window import MainWindow

    apps = discover_apps(repo_root / "apps")[:2]
    manager = ProcessManager(tmp_path / "logs")
    qt_app = QApplication.instance() or QApplication([])
    window_started = time.perf_counter()
    window = MainWindow(config, apps, object(), manager)
    window.show()
    qt_app.processEvents()
    launcher_window_seconds = time.perf_counter() - window_started

    one_started = time.perf_counter()
    one_state = manager.start(apps[0], _environment(tmp_path, apps[0]))
    one_app_seconds = time.perf_counter() - one_started
    one_tree_size, one_memory = _process_tree_rss(psutil, one_state)
    manager.stop_all()

    two_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        two_states = list(executor.map(lambda app: manager.start(app, _environment(tmp_path, app)), apps))
    two_app_seconds = time.perf_counter() - two_started
    two_tree_metrics = [_process_tree_rss(psutil, state) for state in two_states]
    manager.stop_all()
    window.close()

    metrics = {
        "launcher_window_seconds": round(launcher_window_seconds, 3),
        "one_app_startup_seconds": round(one_app_seconds, 3),
        "one_app_process_tree_size": one_tree_size,
        "one_app_memory_mib": round(one_memory / 1024 / 1024, 2),
        "two_app_wall_seconds": round(two_app_seconds, 3),
        "two_app_process_tree_sizes": [size for size, _ in two_tree_metrics],
        "two_app_total_memory_mib": round(sum(memory for _, memory in two_tree_metrics) / 1024 / 1024, 2),
    }
    print("AUDIT_SCALE_METRICS=" + json.dumps(metrics, sort_keys=True))


def test_five_concurrent_apps_and_twenty_lifecycle_cycles(repo_root, tmp_path):
    psutil = pytest.importorskip("psutil")
    apps = discover_apps(repo_root / "apps")[:5]
    manager = ProcessManager(tmp_path / "logs")
    parent = psutil.Process()
    parent_memory_before = parent.memory_info().rss
    process_count_before = len(parent.children(recursive=True))
    launch_durations: dict[str, float] = {}

    def launch(app):
        started = time.perf_counter()
        state = manager.start(app, _environment(tmp_path, app))
        launch_durations[app.id] = time.perf_counter() - started
        return state

    wall_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as executor:
        states = list(executor.map(launch, apps))
    five_app_wall_seconds = time.perf_counter() - wall_started

    try:
        assert len({state.port for state in states}) == 5
        assert all(state.process.poll() is None for state in states)
        process_trees = {}
        for state in states:
            root = psutil.Process(state.process_id)
            process_trees[state.app_id] = [root, *root.children(recursive=True)]
        child_memory = {
            app_id: sum(process.memory_info().rss for process in processes)
            for app_id, processes in process_trees.items()
        }
        for processes in process_trees.values():
            for process in processes:
                process.cpu_percent(interval=None)
        time.sleep(0.5)
        child_idle_cpu = {
            app_id: round(sum(process.cpu_percent(interval=None) for process in processes), 2)
            for app_id, processes in process_trees.items()
        }
        process_tree_sizes = {app_id: len(processes) for app_id, processes in process_trees.items()}
    finally:
        five_ports = [state.port for state in states]
        cleanup_started = time.perf_counter()
        manager.stop_all()
        five_app_cleanup_seconds = time.perf_counter() - cleanup_started

    assert all(state.process.poll() is not None for state in states)
    port_deadline = time.monotonic() + 5
    while not all(manager.port_manager.is_available(port) for port in five_ports) and time.monotonic() < port_deadline:
        time.sleep(0.05)
    five_app_port_release_seconds = time.perf_counter() - cleanup_started
    assert all(manager.port_manager.is_available(port) for port in five_ports)

    cycle_app = apps[0]
    cycle_durations = []
    cycle_ports = []
    for _ in range(20):
        started = time.perf_counter()
        state = manager.start(cycle_app, _environment(tmp_path, cycle_app))
        cycle_ports.append(state.port)
        manager.stop(cycle_app.id, timeout_seconds=3)
        cycle_durations.append(time.perf_counter() - started)

    process_count_after = len(parent.children(recursive=True))
    parent_memory_after = parent.memory_info().rss
    assert process_count_after == process_count_before
    assert all(manager.port_manager.is_available(port) for port in cycle_ports)

    metrics = {
        "five_app_wall_seconds": round(five_app_wall_seconds, 3),
        "five_app_launch_seconds": {key: round(value, 3) for key, value in launch_durations.items()},
        "five_app_child_memory_mib": {key: round(value / 1024 / 1024, 2) for key, value in child_memory.items()},
        "five_app_total_memory_mib": round(sum(child_memory.values()) / 1024 / 1024, 2),
        "five_app_idle_cpu_percent": child_idle_cpu,
        "five_app_process_tree_sizes": process_tree_sizes,
        "five_app_cleanup_seconds": round(five_app_cleanup_seconds, 3),
        "five_app_port_release_seconds": round(five_app_port_release_seconds, 3),
        "twenty_cycle_total_seconds": round(sum(cycle_durations), 3),
        "twenty_cycle_mean_seconds": round(sum(cycle_durations) / len(cycle_durations), 3),
        "twenty_cycle_unique_ports": len(set(cycle_ports)),
        "parent_memory_before_mib": round(parent_memory_before / 1024 / 1024, 2),
        "parent_memory_after_mib": round(parent_memory_after / 1024 / 1024, 2),
        "process_count_before": process_count_before,
        "process_count_after": process_count_after,
    }
    print("AUDIT_METRICS=" + json.dumps(metrics, sort_keys=True))


def test_large_health_log_scan(tmp_path):
    psutil = pytest.importorskip("psutil")
    log_path = tmp_path / "large.log"
    marker = (
        "\nYou can now view your Streamlit app in your browser.\n"
        "http://127.0.0.1:63123\n"
    )
    log_path.write_text(("x" * (64 * 1024 * 1024)) + marker, encoding="utf-8")
    process = psutil.Process()
    memory_before = process.memory_info().rss
    tracemalloc.start()
    started = time.perf_counter()

    url = HealthChecker.streamlit_ready_url_from_log(log_path, expected_port=63123)

    elapsed = time.perf_counter() - started
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memory_after = process.memory_info().rss
    assert url == "http://127.0.0.1:63123"
    metrics = {
        "health_log_size_mib": round(log_path.stat().st_size / 1024 / 1024, 2),
        "health_log_scan_seconds": round(elapsed, 3),
        "health_log_scan_rss_delta_mib": round((memory_after - memory_before) / 1024 / 1024, 2),
        "health_log_scan_peak_python_mib": round(peak_memory / 1024 / 1024, 2),
    }
    print("AUDIT_LOG_METRICS=" + json.dumps(metrics, sort_keys=True))
