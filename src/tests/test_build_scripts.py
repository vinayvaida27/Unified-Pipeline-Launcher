from pathlib import Path

from build_scripts.create_pyinstaller_spec import generate_spec


def _minimal_project(root: Path) -> None:
    (root / "launcher").mkdir(parents=True)
    (root / "launcher" / "__main__.py").write_text("print('launcher')\n", encoding="utf-8")
    (root / "assets" / "launcher").mkdir(parents=True)


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


def test_vbs_launcher_runs_pythonw_hidden(repo_root):
    script = (repo_root / "START_LAUNCHER.vbs").read_text(encoding="utf-8")

    assert "WScript.ScriptFullName" in script
    assert 'runtime\\pythonw.exe' in script
    assert '""" -m launcher --config """' in script
    assert "shell.Run command, 0, False" in script
    assert "launcher.exe" in script


def test_debug_batch_is_not_user_facing_launcher(repo_root):
    assert not (repo_root / "START_LAUNCHER.bat").exists()

    script = (repo_root / "START_LAUNCHER_DEBUG.bat").read_text(encoding="utf-8")
    assert "debug console" in script.lower()
    assert "START_LAUNCHER.lnk or START_LAUNCHER.vbs" in script
    assert "python.exe" in script
    assert "pythonw.exe" not in script


def test_shortcut_creator_uses_pythonw_without_terminal(source_root):
    script = (source_root / "scripts" / "create_launcher_shortcut.ps1").read_text(encoding="utf-8")

    assert "START_LAUNCHER.lnk" in script
    assert 'runtime\\pythonw.exe' in script
    assert '-m launcher --config' in script
    assert "$Shortcut.WindowStyle = 7" in script
    assert "Start-Process $ShortcutPath" in script
    assert "START_LAUNCHER.bat" in script
    assert "START_LAUNCHER_DEBUG.bat" in script
    assert "Rename-Item" in script


def test_release_build_copies_launcher_requirements(source_root):
    build_script = (source_root / "build_scripts" / "build.py").read_text(encoding="utf-8")
    verify_script = (source_root / "scripts" / "verify_release.ps1").read_text(encoding="utf-8")

    assert "requirements-launcher.txt" in build_script
    assert "requirements-launcher.txt" in verify_script
    assert "START_LAUNCHER.vbs" in build_script
    assert "START_LAUNCHER_DEBUG.bat" in build_script
