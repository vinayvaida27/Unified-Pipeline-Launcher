from __future__ import annotations

import json

from launcher.dependency_manager import scan_python_dependencies, update_runtime_dependencies


def test_scans_unique_third_party_imports(copied_apps, tmp_path):
    extra = copied_apps / "01_hello_pipeline" / "extra.py"
    extra.write_text("import pandas\nfrom PIL import Image\nimport streamlit\n", encoding="utf-8")
    packages = scan_python_dependencies(copied_apps)
    assert "pandas" in packages
    assert "Pillow" in packages
    assert packages.count("pandas") == 1
    assert "streamlit" not in packages


def test_skips_local_project_modules(copied_apps):
    app_dir = copied_apps / "01_hello_pipeline"
    (app_dir / "initialization_methods.py").write_text("def initialize(): pass\n", encoding="utf-8")
    (app_dir / "extra.py").write_text("from initialization_methods import initialize\n", encoding="utf-8")

    assert "initialization_methods" not in scan_python_dependencies(copied_apps)


def test_updates_only_missing_packages(monkeypatch, copied_apps, tmp_path):
    (copied_apps / "01_hello_pipeline" / "extra.py").write_text("import pandas\n", encoding="utf-8")
    runtime = tmp_path / "python.exe"
    runtime.write_text("", encoding="utf-8")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if "-c" in command:
            class Result:
                stdout = "pandas\n"
            return Result()
        return None

    monkeypatch.setattr("launcher.dependency_manager.subprocess.run", run)
    result = update_runtime_dependencies(copied_apps, runtime, tmp_path / "state")
    assert "pandas" in result["missing"]
    assert calls[-1][-1] == "pandas"
    assert json.loads((tmp_path / "state" / "installed-packages.json").read_text(encoding="utf-8"))["packages"] == result["packages"]
