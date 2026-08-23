from __future__ import annotations

import pytest

from launcher.app_discovery import discover_apps
from launcher.local_cache import LocalCacheManager


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
    assert (cached_python.parent / ".runtime_source_path.txt").read_text(encoding="utf-8") == str(source_runtime)


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
