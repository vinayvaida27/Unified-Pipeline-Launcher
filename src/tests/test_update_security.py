"""Synthetic filesystem regressions for download and release trust boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from launcher.exceptions import RuntimeDownloadError, UpdateError
from launcher.models import RuntimeDownloadConfig
from launcher.runtime_downloader import RuntimeDownloader
from launcher.update_manager import UpdateManager


def downloader_for(temp_config, version="3.11.9"):
    download = RuntimeDownloadConfig(
        enabled=True,
        version=version,
        url="https://example.invalid/python.nupkg",
        sha256="0" * 64,
    )
    return RuntimeDownloader(replace(temp_config, runtime=replace(temp_config.runtime, download=download)))


@pytest.mark.parametrize("version", ["..", "../victim", r"..\victim", "", ".", "3.11.9:stream"])
def test_download_version_cannot_escape_cache(temp_config, version):
    with pytest.raises(RuntimeDownloadError):
        _ = downloader_for(temp_config, version).runtime_dir


def test_cached_marker_cannot_select_external_executable(temp_config, tmp_path):
    downloader = downloader_for(temp_config)
    other_python = tmp_path / "other" / "python.exe"
    other_python.parent.mkdir()
    other_python.write_text("untrusted", encoding="utf-8")
    downloader.marker_path.parent.mkdir(parents=True)
    downloader.marker_path.write_text(json.dumps({
        "sha256": downloader.download.sha256,
        "version": downloader.download.version,
        "url": downloader.download.url,
        "python_path": str(other_python),
    }), encoding="utf-8")
    assert downloader.cached_python() is None


def test_archive_prefix_sibling_is_rejected_before_extraction(temp_config, tmp_path):
    downloader = downloader_for(temp_config)
    archive_path = tmp_path / "runtime.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("tools/python.exe", "placeholder")
        archive.writestr("../.3.11.9.staging-sibling/payload.txt", "untrusted")
    with pytest.raises(RuntimeDownloadError, match="unsafe"):
        downloader._extract(archive_path)
    assert not downloader.runtime_dir.exists()


def test_download_extraction_preserves_existing_runtime(temp_config, tmp_path):
    downloader = downloader_for(temp_config)
    downloader.runtime_dir.mkdir(parents=True)
    previous = downloader.runtime_dir / "python.exe"
    previous.write_text("previous usable runtime", encoding="utf-8")
    archive_path = tmp_path / "runtime.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("tools/python.exe", "replacement")
    with pytest.raises(RuntimeDownloadError, match="existing|Existing"):
        downloader._extract(archive_path)
    assert previous.read_text(encoding="utf-8") == "previous usable runtime"


@pytest.mark.parametrize("version", ["..", "../victim", r"..\victim", "", ".", "1.0.0:stream"])
def test_release_version_cannot_delete_outside_staging(tmp_path, version):
    source = tmp_path / "source"
    source.mkdir()
    (source / "payload.txt").write_text("release", encoding="utf-8")
    cache = tmp_path / "cache"
    victim = cache / "victim"
    victim.mkdir(parents=True)
    (victim / "keep.txt").write_text("user data", encoding="utf-8")
    with pytest.raises(UpdateError):
        UpdateManager(None, cache).stage_release(source, version)
    assert (victim / "keep.txt").read_text(encoding="utf-8") == "user data"


def test_activation_does_not_replace_an_existing_release(tmp_path):
    manager = UpdateManager(None, tmp_path)
    existing = tmp_path / "releases" / "1.0.0"
    existing.mkdir(parents=True)
    (existing / "keep.txt").write_text("running release", encoding="utf-8")
    staged = tmp_path / "staging" / "1.0.0"
    staged.mkdir(parents=True)
    (staged / "payload.txt").write_text("replacement", encoding="utf-8")
    with pytest.raises(UpdateError, match="existing|already"):
        manager.activate_staged_release(staged, "1.0.0")
    assert (existing / "keep.txt").read_text(encoding="utf-8") == "running release"
    assert (staged / "payload.txt").exists()


def test_activation_rejects_staging_outside_cache(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    external = tmp_path / "user-files"
    external.mkdir()
    with pytest.raises(UpdateError):
        UpdateManager(None, cache).activate_staged_release(external, "1.0.0")
    assert external.exists()


def test_activation_cannot_move_user_applications_inside_cache(tmp_path):
    applications = tmp_path / "apps"
    applications.mkdir()
    (applications / "keep.txt").write_text("user applications", encoding="utf-8")
    with pytest.raises(UpdateError):
        UpdateManager(None, tmp_path).activate_staged_release(applications, "1.0.0")
    assert (applications / "keep.txt").read_text(encoding="utf-8") == "user applications"


def test_separate_updates_keep_separate_staging(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "payload.txt").write_text("release", encoding="utf-8")
    manager = UpdateManager(None, tmp_path / "cache")
    first = manager.stage_release(source, "1.0.0")
    second = manager.stage_release(source, "1.0.0")
    assert first != second
    assert (first / "payload.txt").read_text(encoding="utf-8") == "release"
    assert (second / "payload.txt").read_text(encoding="utf-8") == "release"


def test_failed_active_marker_keeps_previous_selection(tmp_path, monkeypatch):
    marker = tmp_path / "active_version.json"
    marker.write_text('{"platform_version": "0.9.0"}\n', encoding="utf-8")
    staged = tmp_path / "staging" / "1.0.0"
    staged.mkdir(parents=True)
    (staged / "payload.txt").write_text("new release", encoding="utf-8")

    def fail_replace(*args):
        raise OSError("synthetic disk full")

    monkeypatch.setattr("launcher.path_utils.os.replace", fail_replace)
    with pytest.raises(OSError, match="disk full"):
        UpdateManager(None, tmp_path).activate_staged_release(staged, "1.0.0")
    assert json.loads(marker.read_text(encoding="utf-8"))["platform_version"] == "0.9.0"
    assert (tmp_path / "releases" / "1.0.0" / "payload.txt").exists()


@pytest.mark.parametrize("url", ["file:///C:/runtime.zip", "http://example.invalid/python.zip"])
def test_download_rejects_non_https_before_opening(temp_config, monkeypatch, url):
    downloader = downloader_for(temp_config)
    downloader.download = replace(downloader.download, url=url)

    def unexpected_open(*args, **kwargs):
        raise AssertionError("Unsupported URL reached downloader")

    monkeypatch.setattr("launcher.runtime_downloader.urlopen", unexpected_open)
    with pytest.raises(RuntimeDownloadError, match="HTTPS"):
        downloader.ensure_runtime()


@pytest.mark.skipif(os.name != "nt", reason="Requires a real Windows directory junction")
@pytest.mark.parametrize("internal", [False, True])
def test_staging_rejects_windows_junction_escape(tmp_path, internal):
    cache = tmp_path / "cache"
    cache.mkdir()
    outside = cache / "apps" if internal else tmp_path / "outside"
    outside.mkdir()
    protected = outside / "keep.txt"
    protected.write_text("user data", encoding="utf-8")
    source = tmp_path / "source"
    source.mkdir()
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command",
         "New-Item -ItemType Junction -Path $env:ECC_TEST_LINK -Target $env:ECC_TEST_TARGET | Out-Null"],
        env={**os.environ, "ECC_TEST_LINK": str(cache / "staging"), "ECC_TEST_TARGET": str(outside)},
        check=True,
        capture_output=True,
    )
    with pytest.raises(UpdateError, match="escapes"):
        UpdateManager(None, cache).stage_release(source, "1.0.0")
    with pytest.raises(UpdateError, match="escapes"):
        UpdateManager(None, cache).activate_staged_release(outside, "1.0.0")
    assert protected.read_text(encoding="utf-8") == "user data"


@pytest.mark.skipif(os.name != "nt", reason="Requires a real Windows directory junction")
def test_downloader_rejects_internal_cache_junction(temp_config):
    downloader = downloader_for(temp_config)
    cache = temp_config.paths.local_cache_directory
    apps = cache / "apps"
    apps.mkdir(parents=True)
    downloader.downloads_dir.parent.mkdir(parents=True)
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command",
         "New-Item -ItemType Junction -Path $env:ECC_TEST_LINK -Target $env:ECC_TEST_TARGET | Out-Null"],
        env={**os.environ, "ECC_TEST_LINK": str(downloader.downloads_dir), "ECC_TEST_TARGET": str(apps)},
        check=True,
        capture_output=True,
    )
    with pytest.raises(RuntimeDownloadError, match="escapes"):
        _ = downloader.runtime_dir
