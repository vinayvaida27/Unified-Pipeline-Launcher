from __future__ import annotations

import hashlib

import pytest

from launcher.exceptions import ChecksumValidationError
from launcher.update_manager import UpdateManager, compare_semver


def test_compares_semantic_versions():
    assert compare_semver("1.1.0", "1.0.9") == 1
    assert compare_semver("1.0.0", "1.0.0") == 0
    assert compare_semver("1.0.0", "1.0.1") == -1


def test_validates_checksum(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")
    digest = hashlib.sha256(b"hello").hexdigest()
    checksums = tmp_path / "checksums.sha256"
    checksums.write_text(f"{digest} file.txt\n", encoding="utf-8")
    UpdateManager(None, tmp_path).validate_checksum_file(tmp_path, checksums)


def test_rejects_corrupted_file(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")
    checksums = tmp_path / "checksums.sha256"
    checksums.write_text("0" * 64 + " file.txt\n", encoding="utf-8")
    with pytest.raises(ChecksumValidationError):
        UpdateManager(None, tmp_path).validate_checksum_file(tmp_path, checksums)


def test_preserves_old_version_by_versioned_activation(tmp_path):
    manager = UpdateManager(None, tmp_path)
    staging1 = tmp_path / "staging1"
    staging1.mkdir()
    (staging1 / "a.txt").write_text("one", encoding="utf-8")
    manager.activate_staged_release(staging1, "1.0.0")
    staging2 = tmp_path / "staging2"
    staging2.mkdir()
    (staging2 / "a.txt").write_text("two", encoding="utf-8")
    manager.activate_staged_release(staging2, "1.1.0")
    assert (tmp_path / "releases" / "1.0.0" / "a.txt").exists()
    assert (tmp_path / "releases" / "1.1.0" / "a.txt").exists()


def test_handles_unavailable_network_path(tmp_path):
    assert not UpdateManager(tmp_path / "missing", tmp_path).network_available()
