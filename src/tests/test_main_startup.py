from __future__ import annotations

from types import SimpleNamespace

from launcher.main import should_sync_to_local_cache


def _config(sync_to_local_cache: bool):
    return SimpleNamespace(runtime=SimpleNamespace(sync_to_local_cache=sync_to_local_cache))


def test_remote_location_does_not_implicitly_enable_local_cache():
    """Network deployment must launch directly unless caching is explicitly enabled."""

    assert should_sync_to_local_cache(_config(False)) is False


def test_explicit_local_cache_setting_is_honored():
    assert should_sync_to_local_cache(_config(True)) is True
