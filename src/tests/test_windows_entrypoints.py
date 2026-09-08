"""Real Windows wrapper execution with a synthetic executable, never the live runtime."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.name != "nt", reason="Windows entrypoints")]


@pytest.fixture(scope="module")
def runtime_probe(tmp_path_factory):
    root = tmp_path_factory.mktemp("entrypoint-probe")
    source = root / "probe.cs"
    source.write_text('''using System;
using System.IO;
class Probe {
    static int Main(string[] args) {
        File.AppendAllText(Environment.GetEnvironmentVariable("ECC_PROBE_LOG"),
            Path.GetFileName(Environment.GetCommandLineArgs()[0]) + "|" +
            Directory.GetCurrentDirectory() + "|" + string.Join("~", args) + "|" +
            (Environment.GetEnvironmentVariable("PYTHONHOME") ?? "<unset>") + "|" +
            (Environment.GetEnvironmentVariable("PYTHONPATH") ?? "<unset>") + "|" +
            Environment.GetEnvironmentVariable("PYTHONNOUSERSITE") + "\\n");
        if (Array.IndexOf(args, "-m") >= 0) {
            System.Threading.Thread.Sleep(200);
            return int.Parse(Environment.GetEnvironmentVariable("ECC_PROBE_EXIT") ?? "0");
        }
        return int.Parse(Environment.GetEnvironmentVariable("ECC_PROBE_VALIDATE_EXIT") ?? "0");
    }
}''', encoding="utf-8")
    compiler = Path(os.environ["SystemRoot"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not compiler.exists():
        pytest.skip(".NET Framework C# compiler unavailable")
    executable = root / "probe.exe"
    subprocess.run([str(compiler), "/nologo", f"/out:{executable}", str(source)], check=True, capture_output=True)
    return executable


def _deployment(tmp_path, repo_root, runtime_probe, name="release"):
    release = tmp_path / name
    runtime = release / "src/runtime"
    runtime.mkdir(parents=True)
    for name in ("python.exe", "pythonw.exe"):
        shutil.copy2(runtime_probe, runtime / name)
    (release / "src/config").mkdir()
    (release / "src/config/launcher_config.json").write_text("{}", encoding="utf-8")
    for name in ("START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat"):
        shutil.copy2(repo_root / name, release / name)
    return release


def _run(release, tmp_path, entrypoint, exit_code=0, validation_exit=0):
    log = tmp_path / "probe.log"
    env = dict(os.environ, ECC_PROBE_LOG=str(log), ECC_PROBE_EXIT=str(exit_code), ECC_PROBE_VALIDATE_EXIT=str(validation_exit),
               PYTHONHOME="poison-home", PYTHONPATH="poison-path")
    if entrypoint.endswith(".vbs"):
        command = ["cscript.exe", "//nologo", str(release / entrypoint)]
    else:
        # cmd.exe has its own quote grammar; list2cmdline is for ordinary executables.
        command = f'"{os.environ["ComSpec"]}" /d /s /c ""{release / entrypoint}" --silent"'
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, timeout=20)
    return result, log.read_text(encoding="utf-8").splitlines() if log.exists() else []


@pytest.mark.parametrize("entrypoint", ["START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat"])
def test_wrappers_preserve_runtime_exit_status(repo_root, tmp_path, runtime_probe, entrypoint):
    release = _deployment(tmp_path, repo_root, runtime_probe)
    result, calls = _run(release, tmp_path, entrypoint, exit_code=42)
    assert result.returncode == 42, (result.stdout, result.stderr, calls)
    assert any("-m~launcher~--config~" in call for call in calls)


@pytest.mark.parametrize("entrypoint", ["START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat"])
def test_entrypoints_handle_special_paths_and_unrelated_cwd(repo_root, tmp_path, runtime_probe, entrypoint):
    release = _deployment(tmp_path, repo_root, runtime_probe, "release ü (stable) [1] & one's")
    result, calls = _run(release, tmp_path, entrypoint)
    assert result.returncode == 0, (result.stdout, result.stderr)
    launches = [call for call in calls if "-m~launcher~" in call]
    assert len(launches) == 1, calls
    assert str(release / "src") in launches[0]
    assert "--no-local-cache" in launches[0]
    assert launches[0].endswith("|<unset>|<unset>|1"), launches


def test_vbs_reports_rejected_runtime_without_launching(repo_root, tmp_path, runtime_probe):
    release = _deployment(tmp_path, repo_root, runtime_probe)
    result, calls = _run(release, tmp_path, "START_LAUNCHER.vbs", validation_exit=86)
    assert result.returncode != 0
    assert b"START_LAUNCHER_DEBUG.bat" in result.stdout
    assert not any("-m~launcher~" in call for call in calls)


def test_generated_shortcut_targets_vbs_with_literal_arguments(source_root, repo_root, tmp_path, runtime_probe):
    release = _deployment(tmp_path, repo_root, runtime_probe, "release ü (stable) [1]")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(source_root / "scripts/create_launcher_shortcut.ps1"), "-ReleaseDir", str(release)],
        capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    probe = tmp_path / "read-shortcut.ps1"
    probe.write_text('param([string]$Path)\n$s = (New-Object -ComObject WScript.Shell).CreateShortcut($Path)\n'
        '@{target=$s.TargetPath; arguments=$s.Arguments; cwd=$s.WorkingDirectory} | ConvertTo-Json -Compress\n',
        encoding="utf-8-sig")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-File", str(probe), str(release / "START_LAUNCHER.lnk")],
        capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    shortcut = json.loads(result.stdout)
    assert Path(shortcut["target"]).name.lower() == "wscript.exe"
    assert shortcut["arguments"] == f'"{release / "START_LAUNCHER.vbs"}"'
    assert Path(shortcut["cwd"]) == release


def test_source_tree_module_needs_nonisolated_startup(tmp_path):
    package = tmp_path / "launcher"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text("print('trusted source loaded')", encoding="utf-8")
    python = sys._base_executable
    isolated = subprocess.run([python, "-I", "-m", "launcher"], cwd=tmp_path, capture_output=True, timeout=20)
    assert isolated.returncode != 0
    assert b"No module named launcher" in isolated.stderr
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    direct = subprocess.run([python, "-m", "launcher"], cwd=tmp_path, env=env, capture_output=True, timeout=20)
    assert direct.returncode == 0, direct.stderr
    assert b"trusted source loaded" in direct.stdout


def test_batch_rejects_python_executable_without_encodings(repo_root, tmp_path):
    release = tmp_path / "broken runtime [1]"
    runtime = release / "src/runtime"
    runtime.mkdir(parents=True)
    base = Path(sys._base_executable).parent
    shutil.copy2(sys._base_executable, runtime / "python.exe")
    for path in base.glob("*.dll"):
        shutil.copy2(path, runtime / path.name)
    # Explicit isolated search paths make this fixture independent of registry installs.
    (runtime / f"python{sys.version_info.major}{sys.version_info.minor}._pth").write_text("Lib\n", encoding="ascii")
    (release / "src/config").mkdir()
    (release / "src/config/launcher_config.json").write_text("{}", encoding="utf-8")
    shutil.copy2(repo_root / "START_LAUNCHER.bat", release / "START_LAUNCHER.bat")
    result, calls = _run(release, tmp_path, "START_LAUNCHER.bat")
    assert result.returncode != 0
    assert b"encodings" in result.stderr
    assert b"runtime validation failed" in result.stdout
    assert not calls


def test_quality_gate_accepts_supported_startup_and_powershell_comments(source_root):
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(source_root / "scripts/public_quality_gate.ps1"), "-SkipPytest"], capture_output=True, timeout=45)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_checksum_generation_runs_in_windows_powershell_51(source_root, tmp_path):
    import hashlib

    release = tmp_path / "release [stable] (one)"
    (release / "nested").mkdir(parents=True)
    (release / "nested/file.txt").write_bytes(b"synthetic")
    # Windows os.environ uppercases keys; remove case-insensitively.
    env = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(source_root / "scripts/generate_checksums.ps1"), "-Path", str(release)],
        env=env, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (release / "checksums.sha256").read_text(encoding="utf-8-sig").strip() == (
        hashlib.sha256(b"synthetic").hexdigest() + " nested/file.txt")


@pytest.mark.parametrize("skip_pytest", [True, False], ids=["skip-pytest", "with-pytest"])
def test_quality_gate_uses_literal_checkout_paths(repo_root, source_root, tmp_path, runtime_probe, skip_pytest):
    """Run the actual PowerShell gate; synthetic Python records its cwd/args."""
    checkout = tmp_path / "checkout ü [stable] (literal) & one's"
    source = checkout / "src"
    scripts = source / "scripts"
    scripts.mkdir(parents=True)
    for script in (source_root / "scripts").iterdir():
        if script.is_file():
            shutil.copy2(script, scripts / script.name)
    for name in ("pyproject.toml", "uv.lock", "requirements-launcher.txt"):
        shutil.copy2(source_root / name, source / name)
    for name in ("README.md", "LICENSE", "UPDATE_PACKAGES.bat", "START_LAUNCHER.bat",
                 "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat"):
        shutil.copy2(repo_root / name, checkout / name)
    (checkout / "apps").mkdir()
    shutil.copy2(repo_root / "apps/apps.json", checkout / "apps/apps.json")
    interpreter = source / ".venv/Scripts/python.exe"
    interpreter.parent.mkdir(parents=True)
    shutil.copy2(runtime_probe, interpreter)
    log = tmp_path / "gate-python.log"
    env = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
    env.update(ECC_PROBE_LOG=str(log), ECC_PROBE_EXIT="0", ECC_PROBE_VALIDATE_EXIT="0")
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
               str(scripts / "public_quality_gate.ps1")]
    if skip_pytest:
        command.append("-SkipPytest")
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert b"Public quality gate passed." in result.stdout
    calls = log.read_text(encoding="utf-8").splitlines()
    svg_call = next(call for call in calls if "check_svg_icons.py" in call)
    assert svg_call.split("|")[1] == str(source)
    if not skip_pytest:
        pytest_call = next(call for call in calls if "-m~pytest" in call)
        assert pytest_call.split("|")[1] == str(source)
