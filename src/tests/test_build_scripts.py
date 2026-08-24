import json
import os
import subprocess
from pathlib import Path

import pytest

from build_scripts.build import ExeBuilder
from build_scripts.create_pyinstaller_spec import generate_spec


def _minimal_project(root: Path) -> None:
    (root / "launcher").mkdir(parents=True)
    (root / "launcher" / "__main__.py").write_text("print('launcher')\n", encoding="utf-8")
    (root / "assets" / "launcher").mkdir(parents=True)


def test_public_repository_layout_is_minimal(repo_root, source_root):
    assert (source_root / "apps" / "apps.json").is_file()
    assert not (repo_root / "apps").exists()
    assert not (repo_root / "TEST_AUDIT.md").exists()

    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert not any(path.startswith((".agents/", "audit_artifacts/", "src/.autoresearch/")) for path in tracked)
    assert [path for path in tracked if path.endswith(".md")] == ["README.md"]

    pyproject = (source_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "unified-pipeline-launcher"' in pyproject


def test_generate_spec_ignores_invalid_placeholder_icon(tmp_path):
    _minimal_project(tmp_path)
    (tmp_path / "assets" / "launcher" / "launcher.ico").write_text(
        "Launcher icon placeholder.",
        encoding="utf-8",
    )

    spec_path = generate_spec(tmp_path)

    assert "icon=None" in spec_path.read_text(encoding="utf-8")


def test_generate_spec_uses_valid_ico_header(tmp_path):
    _minimal_project(tmp_path)
    icon_path = tmp_path / "assets" / "launcher" / "launcher.ico"
    icon_path.write_bytes(b"\x00\x00\x01\x00\x01\x00")

    spec_path = generate_spec(tmp_path)

    spec_text = spec_path.read_text(encoding="utf-8")
    assert "icon=None" not in spec_text
    assert icon_path.as_posix() in spec_text


def test_launcher_dependencies_install_and_validate(source_root):
    requirements = (source_root / "requirements-launcher.txt").read_text(encoding="utf-8")
    setup_script = (source_root / "scripts" / "prepare_shared_runtime.ps1").read_text(encoding="utf-8")

    assert "PySide6>=6.7,<7" in requirements
    assert "requirements-launcher.txt" in setup_script
    assert 'from PySide6.QtWidgets import QApplication; import streamlit' in setup_script


def test_vbs_launcher_hides_console_without_hiding_gui(repo_root):
    script = (repo_root / "START_LAUNCHER.vbs").read_text(encoding="utf-8")

    assert "WScript.ScriptFullName" in script
    assert 'runtime\\pythonw.exe' in script
    assert '""" -m launcher --config """' in script
    assert "shell.Run command, 1, False" in script
    assert "shell.Run command, 0, False" not in script
    assert "launcher.exe" in script


def test_debug_batch_is_not_user_facing_launcher(repo_root):
    assert not (repo_root / "START_LAUNCHER.bat").exists()

    script = (repo_root / "START_LAUNCHER_DEBUG.bat").read_text(encoding="utf-8")
    assert "debug console" in script.lower()
    assert "START_LAUNCHER.lnk or START_LAUNCHER.vbs" in script
    assert "python.exe" in script
    assert "pythonw.exe" not in script


def test_shortcut_creator_uses_bootstrap_without_terminal(source_root):
    script = (source_root / "scripts" / "create_launcher_shortcut.ps1").read_text(encoding="utf-8")

    assert "START_LAUNCHER.lnk" in script
    assert "START_LAUNCHER.vbs" in script
    assert "$LauncherScript" in script
    assert "$Shortcut.WindowStyle = 7" in script
    assert "Start-Process $ShortcutPath" in script
    assert "START_LAUNCHER.bat" in script
    assert "START_LAUNCHER_DEBUG.bat" in script
    assert "Rename-Item" in script


def test_vbs_bootstrap_prefers_matching_local_runtime_cache(repo_root):
    script = (repo_root / "START_LAUNCHER.vbs").read_text(encoding="utf-8")

    assert "local_cache_directory" in script
    assert ".shared_runtime_ready.json" in script
    assert "FilesMatch" in script
    assert "runtime\\current\\pythonw.exe" in script


@pytest.mark.skipif(os.name != "nt", reason="VBScript bootstrap is Windows-specific")
def test_vbs_bootstrap_parses_without_launching(repo_root, tmp_path):
    script = (repo_root / "START_LAUNCHER.vbs").read_text(encoding="utf-8")
    script = script.replace("shell.Run command, 1, False", "WScript.Echo pythonw")
    probe = tmp_path / "START_LAUNCHER.vbs"
    probe.write_text(script, encoding="utf-8")
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "pythonw.exe").touch()
    marker = '{"prepared_at":"now"}\n'
    (tmp_path / "runtime" / ".shared_runtime_ready.json").write_text(marker, encoding="utf-8")
    cache = tmp_path / "cache"
    cached_runtime = cache / "runtime" / "current"
    cached_runtime.mkdir(parents=True)
    (cached_runtime / "pythonw.exe").touch()
    (cached_runtime / ".shared_runtime_ready.json").write_text(marker, encoding="utf-8")
    (cached_runtime / ".runtime_source_path.txt").write_text(str(tmp_path / "runtime"), encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "launcher_config.json").write_text(
        json.dumps({"paths": {"local_cache_directory": str(cache).replace("\\", "/")}}),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cscript.exe", "//nologo", str(probe)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert str(cached_runtime / "pythonw.exe").lower() in result.stdout.strip().lower()


def test_release_build_copies_launcher_requirements(source_root):
    build_script = (source_root / "build_scripts" / "build.py").read_text(encoding="utf-8")
    verify_script = (source_root / "scripts" / "verify_release.ps1").read_text(encoding="utf-8")

    assert "requirements-launcher.txt" in build_script
    assert "requirements-launcher.txt" in verify_script
    assert "START_LAUNCHER.vbs" in build_script
    assert "START_LAUNCHER_DEBUG.bat" in build_script


def test_release_build_copies_source_apps_into_portable_layout(tmp_path):
    public_root = tmp_path / "project"
    source_root = public_root / "src"
    builder = ExeBuilder(source_root)

    (builder.pyinstaller_dist / "launcher").mkdir(parents=True)
    (builder.pyinstaller_dist / "launcher" / "launcher.exe").touch()
    for name in ("assets", "config", "runtime"):
        (source_root / name).mkdir(parents=True)
    (source_root / "config" / "launcher_config.json").write_text("{}\n", encoding="utf-8")
    (source_root / "apps").mkdir()
    (source_root / "apps" / "apps.json").write_text('{"applications": []}\n', encoding="utf-8")
    (source_root / "requirements-launcher.txt").write_text("PySide6\n", encoding="utf-8")
    for name in ("README.md", "LICENSE", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat"):
        (public_root / name).write_text(name, encoding="utf-8")

    builder.copy_release_files()

    assert (builder.release_dir / "apps" / "apps.json").is_file()
    assert (builder.release_dir / "config" / "launcher_config.json").is_file()
    assert builder.release_dir.name == "Unified-Pipeline-Launcher"


def test_runtime_preparation_detects_portable_release_layout(source_root):
    script = (source_root / "scripts" / "prepare_shared_runtime.ps1").read_text(encoding="utf-8")

    assert 'Join-Path $BuildRelease "runtime\\python.exe"' in script
    assert 'Join-Path $BuildRelease "src\\runtime\\python.exe"' not in script


def test_double_click_installer_keeps_itself_on_failure_and_deletes_after_success(repo_root):
    script = (repo_root / "INSTALL.bat").read_text(encoding="utf-8")

    deploy_call = script.index("deploy_network.ps1")
    failure_guard = script.index('if not "%EXITCODE%"=="0"')
    self_delete = script.index('del /f /q "%~f0"')
    assert deploy_call < failure_guard < self_delete
    assert "INSTALL.bat was kept" in script
    assert "START_LAUNCHER.lnk" in script


def test_double_click_package_updater_calls_all_environment_updater(repo_root):
    script = (repo_root / "UPDATE_PACKAGES.bat").read_text(encoding="utf-8")
    updater = (repo_root / "src" / "scripts" / "update_all_environments.ps1").read_text(encoding="utf-8")

    assert "update_all_environments.ps1" in script
    assert "prepare_shared_runtime.ps1" in updater
    assert "-Upgrade" in updater
    assert "pyvenv.cfg" in updater
    assert "pip check" in updater
    assert "pip install --upgrade" in updater


@pytest.mark.skipif(os.name != "nt", reason="double-click package updater is Windows-specific")
def test_package_updater_dry_run_discovers_without_modifying(repo_root, tmp_path):
    release = tmp_path / "release"
    cache = tmp_path / "cache"
    (release / "src" / "config").mkdir(parents=True)
    (release / "src" / "runtime").mkdir()
    (release / "src" / "runtime" / "python.exe").touch()
    (release / "src" / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    (release / ".venv" / "Scripts").mkdir(parents=True)
    (release / ".venv" / "Scripts" / "python.exe").touch()
    (release / "src" / "apps" / "demo").mkdir(parents=True)
    (release / "src" / "apps" / "demo" / "requirements.txt").write_text("streamlit\n", encoding="utf-8")
    (release / "src" / "apps" / "apps.json").write_text(
        json.dumps({"applications": [{"id": "demo", "folder": "demo"}]}),
        encoding="utf-8",
    )
    (release / "src" / "config" / "launcher_config.json").write_text(
        json.dumps({"paths": {"local_cache_directory": str(cache)}}),
        encoding="utf-8",
    )
    app_venv = cache / "environments" / "demo" / "1.0.0"
    (app_venv / "Scripts").mkdir(parents=True)
    (app_venv / "pyvenv.cfg").touch()
    (app_venv / "Scripts" / "python.exe").touch()

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo_root / "src" / "scripts" / "update_all_environments.ps1"),
            "-ReleaseDir",
            str(release),
            "-DryRun",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "[shared runtime]" in result.stdout
    assert "repository development environment" in result.stdout
    assert "app environment demo\\1.0.0" in result.stdout
    assert "PLAN:" in result.stdout
