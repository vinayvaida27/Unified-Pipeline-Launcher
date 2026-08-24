from __future__ import annotations

import json
from dataclasses import replace

import pytest

from launcher.config_loader import load_platform_config
from launcher.exceptions import ConfigurationError
from launcher.main import should_sync_to_local_cache


def test_valid_config_loads(config, source_root):
    assert config.platform_name == "Unified Pipeline Launcher"
    assert config.paths.apps_directory == (source_root / "apps").resolve()


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


def test_malformed_json_raises_configuration_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Could not read launcher configuration"):
        load_platform_config(path)


def test_remote_runtime_uses_local_cache_even_when_opt_in_is_false(config, monkeypatch):
    config = replace(config, runtime=replace(config.runtime, sync_to_local_cache=False))
    monkeypatch.setattr("launcher.main.is_remote_path", lambda path: path == config.paths.runtime_python)

    assert should_sync_to_local_cache(config)
