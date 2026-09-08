"""Opt-in real HWND acceptance against a disposable, fully prepared deployment.

This is deliberately separate from offscreen Qt tests and simulated SMB paths.
ECC_ACCEPTANCE_ROOT must identify a synthetic directory inside audit_artifacts.
"""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import time
import uuid
from ctypes import wintypes
from pathlib import Path

import pytest

from launcher.app_discovery import discover_apps

pytestmark = [pytest.mark.integration, pytest.mark.native_windows,
              pytest.mark.skipif(os.name != "nt", reason="Real Windows desktop acceptance")]


@pytest.fixture(scope="module")
def native_deployment():
    raw = os.environ.get("ECC_ACCEPTANCE_ROOT")
    if not raw:
        pytest.skip("ECC_ACCEPTANCE_ROOT not set: actual native desktop acceptance NOT RUN")
    root = Path(__file__).resolve().parents[2]
    deployment = Path(raw).resolve()
    assert deployment.is_relative_to(root / "audit_artifacts"), "Only disposable acceptance deployments may be used"
    assert (deployment / "src/runtime/python.exe").is_file(), "Prepare the synthetic runtime first"
    registry = json.loads((deployment / "apps/apps.json").read_text(encoding="utf-8-sig"))
    assert [app["id"] for app in registry["applications"]] == ["synthetic"], "Never test real applications here"
    assert [app.id for app in discover_apps(deployment / "apps")] == ["synthetic"], "Synthetic app must be discoverable"
    shutil.copytree(root / "src/launcher", deployment / "src/launcher", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat"):
        shutil.copy2(root / name, deployment / name)
    config_path = deployment / "src/config/launcher_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    config["platform_name"] = "ECC synthetic native " + uuid.uuid4().hex[:8]
    config["paths"]["local_cache_directory"] = str(deployment / "user-cache")
    config_path.write_text(json.dumps(config), encoding="utf-8")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(root / "src/scripts/create_launcher_shortcut.ps1"), "-ReleaseDir", str(deployment)],
        capture_output=True, check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    return deployment, config["platform_name"]


def _visible_launcher(title):
    user32 = ctypes.windll.user32
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def visit(hwnd, _):
        buffer = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if buffer.value == title and user32.IsWindowVisible(hwnd) and rect.right - rect.left >= 900:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.append((hwnd, pid.value))
        return True

    user32.EnumWindows(visit, 0)
    return found


def _launch_and_close(deployment, title, entrypoint, tmp_path, poison=False, expected_executable=None):
    import psutil

    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON") and key != "QT_QPA_PLATFORM"}
    env["QT_QPA_PLATFORM"] = "windows"
    if poison:
        env.update(PYTHONHOME="poison-home", PYTHONPATH="poison-path", PYTHONSAFEPATH="1", PYTHONPLATLIBDIR="missing-lib")
    if entrypoint.endswith(".exe"):
        command = [str(deployment / entrypoint)]
    elif entrypoint.endswith(".vbs"):
        command = ["wscript.exe", str(deployment / entrypoint)]
    elif entrypoint.endswith(".lnk"):
        script = tmp_path / "open-shortcut.ps1"
        script.write_text('param([string]$Shortcut)\nStart-Process -FilePath $Shortcut -WindowStyle Hidden -Wait\n', encoding="utf-8-sig")
        command = ["powershell.exe", "-NoProfile", "-File", str(script), str(deployment / entrypoint)]
    else:
        command = f'"{os.environ["ComSpec"]}" /d /s /c ""{deployment / entrypoint}" --silent"'
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=tmp_path, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    window = None
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            windows = _visible_launcher(title)
            if windows:
                assert len(windows) == 1
                window, pid = windows[0]
                break
            if process.poll() is not None:
                break
            time.sleep(0.05)
        if window is None:
            if process.poll() is None:
                pytest.fail(f"{entrypoint} did not show the expected native launcher window within 45 seconds")
            pytest.fail(process.communicate(timeout=3)[0].decode(errors="replace") or
                        f"{entrypoint} exited with {process.returncode} before showing the launcher")
        visible = time.perf_counter() - started
        executable = Path(psutil.Process(pid).exe()).resolve()
        if expected_executable is None:
            assert executable.parent == (deployment / "src/runtime").resolve()
        else:
            assert executable == expected_executable.resolve()
        result = ctypes.c_size_t()
        responsive = ctypes.windll.user32.SendMessageTimeoutW(window, 0, 0, 0, 2, 2000, ctypes.byref(result))
        assert responsive, "Native launcher window did not respond to WM_NULL"
        responsive_seconds = time.perf_counter() - started
        ctypes.windll.user32.PostMessageW(window, 0x0010, 0, 0)  # WM_CLOSE for this test-owned HWND only.
        output = process.communicate(timeout=20)[0]
        assert process.returncode == 0, output.decode(errors="replace")
        print("NATIVE_TIMING=" + json.dumps({"entrypoint": entrypoint, "poisoned_environment": poison,
            "visible_seconds": round(visible, 3), "responsive_seconds": round(responsive_seconds, 3)}))
    finally:
        if window and ctypes.windll.user32.IsWindow(window):
            ctypes.windll.user32.PostMessageW(window, 0x0010, 0, 0)
        if process.poll() is None:
            for child in psutil.Process(process.pid).children(recursive=True):
                child.kill()
            process.kill()
        process.communicate(timeout=10)


@pytest.mark.parametrize("entrypoint", ["START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat", "START_LAUNCHER.lnk"])
def test_actual_entrypoint_shows_responsive_native_window(native_deployment, tmp_path, entrypoint):
    deployment, title = native_deployment
    _launch_and_close(deployment, title, entrypoint, tmp_path)


def test_actual_source_startup_ignores_inherited_python_flags(native_deployment, tmp_path):
    deployment, title = native_deployment
    _launch_and_close(deployment, title, "START_LAUNCHER.bat", tmp_path, poison=True)


def test_complete_deployment_can_move_and_regenerate_shortcut(native_deployment, tmp_path):
    deployment, title = native_deployment
    audit_root = Path(__file__).resolve().parents[2] / "audit_artifacts"
    relocated = (deployment.parent / ("Relocated [ECC] (Unicode é) " + uuid.uuid4().hex[:8])).resolve()
    assert deployment.resolve().is_relative_to(audit_root.resolve())
    assert relocated.is_relative_to(audit_root.resolve())
    assert not relocated.exists()
    config_path = deployment / "src/config/launcher_config.json"
    original_config = config_path.read_bytes()
    shortcut_path = deployment / "START_LAUNCHER.lnk"
    original_shortcut = shortcut_path.read_bytes()
    config = json.loads(original_config)
    config["paths"]["local_cache_directory"] = str(relocated / "user-cache")
    moved = False
    try:
        config_path.write_text(json.dumps(config), encoding="utf-8")
        deployment.rename(relocated)
        moved = True
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(["powershell.exe", "-NoProfile", "-File",
            str(root / "src/scripts/create_launcher_shortcut.ps1"), "-ReleaseDir", str(relocated)],
            capture_output=True, check=False, timeout=30)
        assert result.returncode == 0, result.stderr
        _launch_and_close(relocated, title, "START_LAUNCHER.lnk", tmp_path, poison=True)
    finally:
        if moved:
            relocated.rename(deployment)
        config_path.write_bytes(original_config)
        shortcut_path.write_bytes(original_shortcut)


@pytest.fixture(scope="module")
def frozen_deployment():
    raw = os.environ.get("ECC_FROZEN_ACCEPTANCE_ROOT")
    if not raw:
        pytest.skip("ECC_FROZEN_ACCEPTANCE_ROOT not set: built EXE acceptance NOT RUN")
    root = Path(__file__).resolve().parents[2]
    deployment = Path(raw).resolve()
    assert deployment.is_relative_to(root / "audit_artifacts"), "Only disposable acceptance deployments may be used"
    assert (deployment / "launcher.exe").is_file()
    assert (deployment / "runtime/python.exe").is_file()
    registry = json.loads((deployment / "apps/apps.json").read_text(encoding="utf-8-sig"))
    assert [app["id"] for app in registry["applications"]] == ["synthetic"], "Never test real applications here"
    assert [app.id for app in discover_apps(deployment / "apps")] == ["synthetic"], "Synthetic app must be discoverable"
    config_path = deployment / "config/launcher_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    config["platform_name"] = "ECC synthetic frozen " + uuid.uuid4().hex[:8]
    config["paths"]["local_cache_directory"] = str(deployment / "user-cache")
    config_path.write_text(json.dumps(config), encoding="utf-8")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-File",
        str(root / "src/scripts/create_launcher_shortcut.ps1"), "-ReleaseDir", str(deployment)],
        capture_output=True, check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    return deployment, config["platform_name"]


@pytest.mark.parametrize("entrypoint", ["launcher.exe", "START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat", "START_LAUNCHER.lnk"])
def test_built_entrypoint_shows_responsive_native_window(frozen_deployment, tmp_path, entrypoint):
    deployment, title = frozen_deployment
    _launch_and_close(deployment, title, entrypoint, tmp_path, poison=True,
                      expected_executable=deployment / "launcher.exe")
