from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from launcher.app_discovery import discover_apps
from launcher.local_cache import LocalCacheManager
from launcher.exceptions import RuntimeValidationError, UpdateError


@pytest.fixture(autouse=True)
def _accept_fake_test_runtimes(monkeypatch):
    monkeypatch.setattr(LocalCacheManager, "_runtime_is_self_contained", staticmethod(lambda _python: True))


def test_syncs_app_source_to_local_cache(tmp_path, repo_root):
    app = discover_apps(repo_root / "apps")[0]
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()

    cached_app = cache.sync_app_to_local_cache(app)

    assert cached_app.app_dir != app.app_dir
    assert cached_app.app_dir == (tmp_path / "cache" / "apps" / app.id / app.version).resolve()
    assert cached_app.entrypoint.exists()
    assert cached_app.entrypoint.parent == cached_app.app_dir
    assert cached_app.icon.exists()
    assert cached_app.requirements.exists()


def test_sync_refreshes_when_source_changes(tmp_path, copied_apps):
    app = discover_apps(copied_apps)[0]
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()

    first_cached = cache.sync_app_to_local_cache(app)
    original_text = first_cached.entrypoint.read_text(encoding="utf-8")
    app.entrypoint.write_text(original_text + "\n# changed\n", encoding="utf-8")

    refreshed = cache.sync_app_to_local_cache(app)

    assert "# changed" in refreshed.entrypoint.read_text(encoding="utf-8")


def test_syncs_runtime_to_local_cache(tmp_path):
    source_runtime = tmp_path / "network_share" / "runtime"
    source_runtime.mkdir(parents=True)
    runtime_python = source_runtime / "python.exe"
    runtime_python.write_text("fake python", encoding="utf-8")
    (source_runtime / "Lib").mkdir()
    (source_runtime / "Lib" / "module.py").write_text("x = 1", encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()

    cached_python = cache.sync_runtime_to_local_cache(runtime_python)

    assert cached_python == (tmp_path / "cache" / "runtime" / "current" / "python.exe").resolve()
    assert cached_python.exists()
    assert (cached_python.parent / "Lib" / "module.py").exists()


def test_sync_runtime_refreshes_when_source_changes(tmp_path):
    source_runtime = tmp_path / "network_share" / "runtime"
    source_runtime.mkdir(parents=True)
    runtime_python = source_runtime / "python.exe"
    runtime_python.write_text("version 1", encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()
    cache.sync_runtime_to_local_cache(runtime_python)

    runtime_python.write_text("version 2", encoding="utf-8")
    cached_python = cache.sync_runtime_to_local_cache(runtime_python)

    assert cached_python.read_text(encoding="utf-8") == "version 2"


def test_shared_runtime_marker_avoids_full_source_rescan(tmp_path, monkeypatch):
    source_runtime = tmp_path / "network_share" / "runtime"
    source_runtime.mkdir(parents=True)
    runtime_python = source_runtime / "python.exe"
    runtime_python.write_text("fake python", encoding="utf-8")
    (source_runtime / ".shared_runtime_ready.json").write_text('{"prepared_at":"now"}\n', encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()
    monkeypatch.setattr(
        cache,
        "_fingerprint_directory_metadata",
        lambda directory: pytest.fail("prepared runtimes should use their release marker"),
    )

    first = cache.sync_runtime_to_local_cache(runtime_python)
    second = cache.sync_runtime_to_local_cache(runtime_python)

    assert first == second


def test_runtime_fingerprint_ignores_equivalent_source_path_aliases(tmp_path):
    sources = [tmp_path / "mapped-drive" / "runtime", tmp_path / "unc-share" / "runtime"]
    timestamp = 1_700_000_000_000_000_000
    for source in sources:
        source.mkdir(parents=True)
        python = source / "python.exe"
        python.write_text("same runtime", encoding="utf-8")
        os.utime(python, ns=(timestamp, timestamp))
        (source / ".shared_runtime_ready.json").write_text('{"prepared_at":"same"}\n', encoding="utf-8")

    fingerprints = [LocalCacheManager._runtime_source_fingerprint(source, source / "python.exe") for source in sources]

    assert fingerprints[0] == fingerprints[1]


def test_missing_cached_python_forces_runtime_refresh(tmp_path):
    source_runtime = tmp_path / "network_share" / "runtime"
    source_runtime.mkdir(parents=True)
    runtime_python = source_runtime / "python.exe"
    runtime_python.write_text("source python", encoding="utf-8")
    (source_runtime / ".shared_runtime_ready.json").write_text('{"prepared_at":"now"}\n', encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()
    cached_python = cache.sync_runtime_to_local_cache(runtime_python)
    cached_python.unlink()

    refreshed_python = cache.sync_runtime_to_local_cache(runtime_python)

    assert refreshed_python.read_text(encoding="utf-8") == "source python"


def test_non_relocatable_cached_runtime_is_replaced(tmp_path, monkeypatch):
    source_runtime = tmp_path / "network_share" / "runtime"
    source_runtime.mkdir(parents=True)
    runtime_python = source_runtime / "python.exe"
    runtime_python.write_text("self-contained", encoding="utf-8")
    (source_runtime / ".shared_runtime_ready.json").write_text('{"prepared_at":"now"}\n', encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()
    monkeypatch.setattr(
        cache,
        "_runtime_is_self_contained",
        lambda python: python.read_text(encoding="utf-8") == "self-contained",
    )
    cached_python = cache.sync_runtime_to_local_cache(runtime_python)
    cached_python.write_text("prefix points to network source", encoding="utf-8")

    refreshed_python = cache.sync_runtime_to_local_cache(runtime_python)

    assert refreshed_python.read_text(encoding="utf-8") == "self-contained"
    assert cache.runtime_cache_refreshed


def test_real_runtime_probe_ignores_poisoned_python_environment(repo_root, monkeypatch):
    python = repo_root / "src" / "runtime" / "python.exe"
    if not python.is_file():
        pytest.skip("bundled runtime is not present")
    monkeypatch.undo()
    monkeypatch.setenv("PYTHONHOME", str(repo_root / "src"))
    monkeypatch.setenv("PYTHONPATH", str(repo_root / "src"))

    assert LocalCacheManager._runtime_is_self_contained(python)


def test_interrupted_app_refresh_keeps_last_good_cache(tmp_path, copied_apps, monkeypatch):
    app = discover_apps(copied_apps)[0]
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()
    cached = cache.sync_app_to_local_cache(app)
    last_good = cached.entrypoint.read_text(encoding="utf-8")
    app.entrypoint.write_text(last_good + "\n# source changed\n", encoding="utf-8")
    def interrupted_copy(source, destination, **kwargs):
        destination.mkdir(parents=True)
        (destination / "partial.tmp").write_text("partial", encoding="utf-8")
        raise OSError("simulated network interruption")

    monkeypatch.setattr("launcher.local_cache.shutil.copytree", interrupted_copy)

    with pytest.raises(OSError, match="simulated network interruption"):
        cache.sync_app_to_local_cache(app)

    assert cached.entrypoint.read_text(encoding="utf-8") == last_good


def test_corrupt_cached_app_is_refreshed_from_source(tmp_path, copied_apps):
    app = discover_apps(copied_apps)[0]
    cache = LocalCacheManager(tmp_path / "cache")
    cache.ensure_directories()
    cached = cache.sync_app_to_local_cache(app)
    expected = app.entrypoint.read_text(encoding="utf-8")
    cached.entrypoint.write_text("corrupt cache\n", encoding="utf-8")

    refreshed = cache.sync_app_to_local_cache(app)

    assert refreshed.entrypoint.read_text(encoding="utf-8") == expected


def test_invalid_staged_runtime_preserves_last_usable_runtime(tmp_path, monkeypatch):
    source = tmp_path / "source runtime [ü]" / "python.exe"
    source.parent.mkdir()
    source.write_text("usable runtime", encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "local-installed")
    cached = cache.sync_runtime_to_local_cache(source)
    source.write_text("missing encodings", encoding="utf-8")
    monkeypatch.setattr(cache, "_runtime_is_self_contained", lambda python: python.read_text() == "usable runtime")

    with pytest.raises(RuntimeValidationError):
        cache.sync_runtime_to_local_cache(source)

    assert cached.read_text(encoding="utf-8") == "usable runtime"


@pytest.mark.parametrize("target", ["runtime", "app"])
def test_failed_activation_restores_previous_cache(tmp_path, copied_apps, monkeypatch, target):
    cache = LocalCacheManager(tmp_path / "cache")
    if target == "runtime":
        source = tmp_path / "source" / "python.exe"
        source.parent.mkdir()
        source.write_text("version 1", encoding="utf-8")
        sync = lambda: cache.sync_runtime_to_local_cache(source)
        cached = sync()
    else:
        app = discover_apps(copied_apps)[0]
        source = app.entrypoint
        sync = lambda: cache.sync_app_to_local_cache(app).entrypoint
        cached = sync()
    last_good = cached.read_text(encoding="utf-8")
    source.write_text(last_good + "\n# changed", encoding="utf-8")
    replace = cache._safe_replace

    def fail_staged_activation(staged, destination, **kwargs):
        if ".staging" in staged.name:
            raise PermissionError("simulated locked activation")
        replace(staged, destination, **kwargs)

    monkeypatch.setattr(cache, "_safe_replace", fail_staged_activation)
    with pytest.raises(PermissionError, match="locked activation"):
        sync()
    assert cached.read_text(encoding="utf-8") == last_good


def test_concurrent_runtime_update_refuses_second_writer(tmp_path, monkeypatch):
    source = tmp_path / "source" / "python.exe"
    source.parent.mkdir()
    source.write_text("version 1", encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cached = cache.sync_runtime_to_local_cache(source)
    source.write_text("version 2", encoding="utf-8")
    lock = cached.parent.parent / ".current.update.lock"
    lock.write_text("another writer", encoding="utf-8")

    with pytest.raises(UpdateError, match="update.lock"):
        cache.sync_runtime_to_local_cache(source)

    assert cached.read_text(encoding="utf-8") == "version 1"
    assert lock.read_text(encoding="utf-8") == "another writer"


def test_runtime_that_fails_after_relocation_rolls_back(tmp_path, monkeypatch):
    source = tmp_path / "source" / "python.exe"
    source.parent.mkdir()
    source.write_text("version 1", encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cached = cache.sync_runtime_to_local_cache(source)
    source.write_text("version 2", encoding="utf-8")
    monkeypatch.setattr(
        cache, "_runtime_is_self_contained",
        lambda python: python.parent.name != "current" or python.read_text() == "version 1",
    )

    with pytest.raises(RuntimeValidationError):
        cache.sync_runtime_to_local_cache(source)

    assert cached.read_text(encoding="utf-8") == "version 1"
    assert not cache.runtime_cache_refreshed


def test_successful_runtime_update_retains_previous_for_rollback(tmp_path):
    source = tmp_path / "source" / "python.exe"
    source.parent.mkdir()
    source.write_text("version 1", encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cached = cache.sync_runtime_to_local_cache(source)
    source.write_text("version 2", encoding="utf-8")

    cache.sync_runtime_to_local_cache(source)

    previous = list(cached.parent.parent.glob(".current.previous.*/python.exe"))
    assert len(previous) == 1
    assert previous[0].read_text(encoding="utf-8") == "version 1"
    assert cached.read_text(encoding="utf-8") == "version 2"


def test_failed_runtime_marker_write_preserves_previous(tmp_path, monkeypatch):
    source = tmp_path / "source" / "python.exe"
    source.parent.mkdir()
    source.write_text("version 1", encoding="utf-8")
    cache = LocalCacheManager(tmp_path / "cache")
    cached = cache.sync_runtime_to_local_cache(source)
    source.write_text("version 2", encoding="utf-8")

    def fail_marker(*args, **kwargs):
        raise PermissionError("read-only marker")

    monkeypatch.setattr("launcher.local_cache.atomic_write_json", fail_marker)
    with pytest.raises(PermissionError, match="read-only marker"):
        cache.sync_runtime_to_local_cache(source)

    assert cached.read_text(encoding="utf-8") == "version 1"
    assert not list(cached.parent.parent.glob(".current.staging.*"))
    assert not list(cached.parent.parent.glob("*.update.lock"))


@pytest.mark.skipif(os.name != "nt", reason="Requires a real Windows directory junction")
@pytest.mark.parametrize("kind", ["runtime", "app"])
def test_cache_update_rejects_parent_junction_into_protected_cache_tree(tmp_path, copied_apps, kind):
    cache = LocalCacheManager(tmp_path / "cache")
    protected = cache.base_dir / "user-files"
    if kind == "runtime":
        source = tmp_path / "source" / "python.exe"
        source.parent.mkdir()
        source.write_text("synthetic runtime", encoding="utf-8")
        victim = protected / "current"
        link = cache.runtime_dir
        sync = lambda: cache.sync_runtime_to_local_cache(source)
    else:
        app = discover_apps(copied_apps)[0]
        victim = protected / app.id / app.version
        link = cache.apps_dir
        sync = lambda: cache.sync_app_to_local_cache(app)
    victim.mkdir(parents=True)
    (victim / "keep.txt").write_text("protected user contents", encoding="utf-8")
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command",
         "New-Item -ItemType Junction -Path $env:ECC_TEST_LINK -Target $env:ECC_TEST_TARGET | Out-Null"],
        env={**os.environ, "ECC_TEST_LINK": str(link), "ECC_TEST_TARGET": str(protected)},
        check=True, capture_output=True,
    )

    with pytest.raises(UpdateError, match="managed cache"):
        sync()

    assert (victim / "keep.txt").read_text(encoding="utf-8") == "protected user contents"
