from __future__ import annotations

import json

import pytest

from launcher.config_loader import load_platform_config
from launcher.exceptions import ConfigurationError


def test_valid_config_loads(config):
    assert config.platform_name == "Unified Pipeline Launcher"
    assert config.paths.apps_directory.name == "apps"


def test_missing_required_field_fails(tmp_path, source_root):
    data = json.loads((source_root / "config" / "launcher_config.json").read_text(encoding="utf-8"))
    data.pop("platform_name")
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_platform_config(path)


def test_environment_variables_expand(tmp_path, monkeypatch, source_root):
    monkeypatch.setenv("LAUNCHER_TEST_CACHE", str(tmp_path / "expanded"))
    data = json.loads((source_root / "config" / "launcher_config.json").read_text(encoding="utf-8"))
    data["paths"]["local_cache_directory"] = "%LAUNCHER_TEST_CACHE%"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    config = load_platform_config(path)
    assert config.paths.local_cache_directory == (tmp_path / "expanded").resolve()


def test_invalid_schema_version_fails(tmp_path, source_root):
    data = json.loads((source_root / "config" / "launcher_config.json").read_text(encoding="utf-8"))
    data["schema_version"] = 99
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_platform_config(path)
