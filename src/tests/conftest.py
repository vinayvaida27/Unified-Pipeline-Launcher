from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from launcher.config_loader import load_platform_config


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def source_root(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture()
def config(source_root: Path):
    return load_platform_config(source_root / "config" / "launcher_config.json")


@pytest.fixture()
def temp_config(tmp_path: Path, repo_root: Path, source_root: Path):
    data = json.loads((source_root / "config" / "launcher_config.json").read_text(encoding="utf-8"))
    data["paths"]["apps_directory"] = str(source_root / "apps")
    data["paths"]["runtime_python"] = str(source_root / "runtime" / "python.exe")
    data["paths"]["local_cache_directory"] = str(tmp_path / "cache")
    path = tmp_path / "launcher_config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_platform_config(path)


@pytest.fixture()
def copied_apps(tmp_path: Path, source_root: Path) -> Path:
    target = tmp_path / "apps"
    shutil.copytree(source_root / "apps", target)
    return target
