from __future__ import annotations

import json

from launcher.dependency_manager import distribution_name_for_import, scan_python_dependencies, update_runtime_dependencies


def test_maps_common_imports_to_distribution_names():
    assert distribution_name_for_import("PIL") == "Pillow"
    assert distribution_name_for_import("Bio") == "biopython"
    assert distribution_name_for_import("sklearn") == "scikit-learn"
    assert distribution_name_for_import("pythoncom") == "pywin32"
    assert distribution_name_for_import("win32com") == "pywin32"
    assert distribution_name_for_import("pandas") == "pandas"


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
    probe_count = 0

    def run(command, **kwargs):
        nonlocal probe_count
        calls.append(command)
        if "-c" in command:
            probe_count += 1
            class Result:
                stdout = "pandas\n" if probe_count == 1 else ""
            return Result()
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return Result()

    monkeypatch.setattr("launcher.dependency_manager.subprocess.run", run)
    result = update_runtime_dependencies(copied_apps, runtime, tmp_path / "state")
    assert "pandas" in result["missing"]
    assert result["installed"] == ["pandas"]
    assert calls[-1][-1] == "pandas"
    assert json.loads((tmp_path / "state" / "installed-packages.json").read_text(encoding="utf-8"))["packages"] == result["packages"]


def test_classifier_import_is_discovered(copied_apps):
    app = copied_apps / "01_hello_pipeline" / "classifier_app.py"
    app.write_text(
        "import pickle\nfrom sklearn.ensemble import RandomForestClassifier\n"
        "with open('classifier.pkl', 'rb') as handle: pickle.load(handle)\n",
        encoding="utf-8",
    )
    assert "scikit-learn" in scan_python_dependencies(copied_apps)
