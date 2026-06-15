from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from launcher.exceptions import RuntimeDownloadError
from launcher.models import RuntimeDownloadConfig
from launcher.runtime_downloader import RuntimeDownloader


def _make_archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("tools/python.exe", "binary-placeholder")
        archive.writestr("tools/python311.dll", "lib-placeholder")
    return buffer.getvalue()


def _configure(temp_config, archive: bytes):
    download = RuntimeDownloadConfig(
        enabled=True,
        version="3.11.9",
        url="https://example.invalid/python.nupkg",
        sha256=hashlib.sha256(archive).hexdigest(),
    )
    runtime = replace(temp_config.runtime, download=download)
    return replace(temp_config, runtime=runtime)


def test_downloads_verifies_and_extracts(temp_config, monkeypatch):
    archive = _make_archive()
    config = _configure(temp_config, archive)
    downloader = RuntimeDownloader(config)

    class FakeResponse(io.BytesIO):
        headers = {"Content-Length": str(len(archive))}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr("launcher.runtime_downloader.urlopen", lambda *a, **k: FakeResponse(archive))

    python_path = downloader.ensure_runtime()
    assert python_path.is_file()
    assert python_path.name == "python.exe"
    # Second call should reuse the cached runtime without downloading again.
    monkeypatch.setattr(
        "launcher.runtime_downloader.urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not re-download")),
    )
    assert downloader.ensure_runtime() == python_path


def test_rejects_bad_checksum(temp_config, monkeypatch):
    archive = _make_archive()
    config = _configure(temp_config, archive)
    bad = replace(config.runtime.download, sha256="0" * 64)
    config = replace(config, runtime=replace(config.runtime, download=bad))
    downloader = RuntimeDownloader(config)

    class FakeResponse(io.BytesIO):
        headers = {"Content-Length": str(len(archive))}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr("launcher.runtime_downloader.urlopen", lambda *a, **k: FakeResponse(archive))
    with pytest.raises(RuntimeDownloadError):
        downloader.ensure_runtime()


def test_disabled_download_raises(temp_config):
    downloader = RuntimeDownloader(temp_config)
    with pytest.raises(RuntimeDownloadError):
        downloader.ensure_runtime()
