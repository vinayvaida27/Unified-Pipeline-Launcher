from __future__ import annotations

import json
from dataclasses import replace

from launcher.app_discovery import discover_apps
from launcher.environment_manager import EnvironmentManager, RuntimeResolver
from launcher.models import RuntimeConfig


def _seed_marker(manager, app, marker_overrides=None):
    """Create the venv python stub and write a marker, returning the env path."""

    env_path = manager.environment_path_for(app)
    python_path = manager.venv_python_for(env_path)
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("", encoding="utf-8")
    marker = {
        "app_id": app.id,
        "app_version": app.version,
        "requirements_sha256": manager.requirements_hash(app.requirements),
        "runtime_fingerprint": manager.runtime_fingerprint(),
    }
    if marker_overrides:
        marker.update(marker_overrides)
    manager.marker_path_for(env_path).write_text(json.dumps(marker), encoding="utf-8")
    return env_path


def _config_with_venvs(config):
    """Return a copy of config with create_virtual_environments=True."""
    new_runtime = replace(config.runtime, create_virtual_environments=True, sync_to_local_cache=True)
    return replace(config, runtime=new_runtime)


def test_calculates_deterministic_environment_path(temp_config, repo_root):
    app = discover_apps(repo_root / "src" / "apps")[0]
    manager = EnvironmentManager(temp_config, repo_root / "fake-python.exe")
    assert manager.environment_path_for(app) == temp_config.paths.local_cache_directory / "environments" / app.id / app.version


def test_detects_ready_marker(temp_config, repo_root):
    app = discover_apps(repo_root / "src" / "apps")[0]
    manager = EnvironmentManager(temp_config, repo_root / "fake-python.exe")
    _seed_marker(manager, app)
    assert manager.is_ready(app)


def test_detects_changed_runtime_fingerprint(temp_config, repo_root):
    app = discover_apps(repo_root / "src" / "apps")[0]
    manager = EnvironmentManager(temp_config, repo_root / "fake-python.exe")
    _seed_marker(manager, app, {"runtime_fingerprint": "stale-runtime"})
    assert not manager.is_ready(app)


def test_detects_changed_requirements_hash(temp_config, repo_root):
    app = discover_apps(repo_root / "src" / "apps")[0]
    manager = EnvironmentManager(temp_config, repo_root / "fake-python.exe")
    _seed_marker(manager, app, {"requirements_sha256": "wrong"})
    assert not manager.is_ready(app)


def test_builds_correct_pip_command(temp_config, repo_root):
    app = discover_apps(repo_root / "src" / "apps")[0]
    manager = EnvironmentManager(temp_config, repo_root / "fake-python.exe")
    command = manager.pip_install_command(app, repo_root / ".venv" / "Scripts" / "python.exe")
    assert command[:4][-3:] == ["-m", "pip", "install"]
    assert "-r" in command


def test_chooses_offline_wheelhouse_when_available(temp_config, copied_apps):
    wheelhouse = copied_apps / "01_hello_pipeline" / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "placeholder.whl").write_text("", encoding="utf-8")
    app = discover_apps(copied_apps)[0]
    manager = EnvironmentManager(temp_config, copied_apps / "fake-python.exe")
    command = manager.pip_install_command(app, copied_apps / "venv-python.exe")
    assert "--no-index" in command
    assert "--find-links" in command


def test_runtime_resolver_can_skip_validation_before_local_sync(temp_config, tmp_path, monkeypatch):
    runtime_python = tmp_path / "network_runtime" / "python.exe"
    runtime_python.parent.mkdir()
    runtime_python.write_text("placeholder", encoding="utf-8")
    object.__setattr__(temp_config.paths, "runtime_python", runtime_python)

    def fail_validate(_python_path):
        raise AssertionError("network runtime should not be executed before local sync")

    resolver = RuntimeResolver(temp_config, development_mode=False)
    monkeypatch.setattr(resolver, "validate", fail_validate)

    assert resolver.resolve(validate=False) == runtime_python


def test_shared_runtime_fast_path(temp_config, repo_root):
    """When create_virtual_environments is False, ensure_environment returns
    the shared runtime state immediately without creating any venv."""

    app = discover_apps(repo_root / "src" / "apps")[0]
    # Default config already has create_virtual_environments=False.
    manager = EnvironmentManager(temp_config, repo_root / "fake-python.exe")
    assert not temp_config.runtime.create_virtual_environments

    progress_messages = []
    state = manager.ensure_environment(app, progress=progress_messages.append)

    assert state.ready is True
    assert state.app_id == app.id
    assert state.python_path == repo_root / "fake-python.exe"
    assert "Using shared runtime" in progress_messages


def test_ensure_environment_runs_full_flow(temp_config, repo_root, monkeypatch):
    """Drive ensure_environment end-to-end with mocks (venv mode).

    Guards against truncated/incomplete method bodies: a fresh environment must
    create the venv, install deps, validate, and write a complete marker without
    raising NameError or leaving steps out.
    """

    # Force venv mode for this test regardless of the default config.
    config = _config_with_venvs(temp_config)
    app = discover_apps(repo_root / "src" / "apps")[0]
    manager = EnvironmentManager(config, repo_root / "fake-python.exe")

    calls = []

    def fake_run_logged(command, log_handle, timeout_seconds, failure_message, error_cls):
        calls.append(command[1] if len(command) > 1 else command[0])

    monkeypatch.setattr(manager, "_run_logged", fake_run_logged)
    # Pretend the venv python exists after creation so the marker write can proceed.
    monkeypatch.setattr(manager, "venv_python_for", lambda env_path: env_path / "python")
    monkeypatch.setattr(
        "launcher.environment_manager.subprocess.check_output",
        lambda *a, **k: "Python 3.11.9",
    )

    progress_messages = []
    state = manager.ensure_environment(app, progress=progress_messages.append)

    assert state.ready is True
    assert state.app_id == app.id
    # venv creation + pip install + streamlit validation all ran.
    assert calls == ["-m", "-m", "-c"]
    assert "Creating virtual environment" in progress_messages
    assert "Installing dependencies" in progress_messages
    # A complete marker was written.
    marker = json.loads(state.marker_path.read_text(encoding="utf-8"))
    assert marker["app_id"] == app.id
    assert marker["runtime_fingerprint"] == manager.runtime_fingerprint()
    assert "installed_at" in marker
