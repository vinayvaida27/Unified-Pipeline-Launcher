"""Prevent unrelated PATH DLLs from contaminating a frozen Windows build."""

import os
import sys
from pathlib import Path

import pytest

from build_scripts.build import ExeBuilder


@pytest.mark.skipif(os.name != "nt", reason="Windows DLL dependency resolution")
def test_pyinstaller_receives_only_selected_python_and_windows_search_paths(
    tmp_path, monkeypatch
):
    unrelated = tmp_path / "unrelated Poppler" / "bin"
    unrelated.mkdir(parents=True)
    monkeypatch.setenv("PATH", str(unrelated))
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "foreign-python"))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "foreign-imports"))
    monkeypatch.setenv("PYTHONPLATLIBDIR", "foreign-lib")
    monkeypatch.setenv("BUILD_TEST_MARKER", "preserved")
    calls = []

    def capture(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr("build_scripts.build.subprocess.run", capture)
    builder = ExeBuilder(tmp_path)
    builder.run_pyinstaller(tmp_path / "launcher.spec")

    command, kwargs = calls.pop()
    env = kwargs.get("env", os.environ)
    actual_paths = [Path(path).resolve() for path in env["PATH"].split(os.pathsep)]
    windows = Path(os.environ["SystemRoot"]).resolve()
    assert actual_paths == list(
        dict.fromkeys(
            [
                Path(sys.executable).resolve().parent,
                Path(sys.base_prefix).resolve(),
                windows / "System32",
                windows,
            ]
        )
    )
    assert unrelated not in actual_paths
    assert not any(key.upper().startswith("PYTHON") for key in env)
    assert env["BUILD_TEST_MARKER"] == "preserved"
    assert os.environ["PATH"] == str(unrelated), "Do not mutate the calling process"
    assert command[:3] == [sys.executable, "-m", "PyInstaller"]
    assert kwargs["cwd"] == builder.project_root
    assert kwargs["check"] is True
