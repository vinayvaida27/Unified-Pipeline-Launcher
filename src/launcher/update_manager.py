"""Safe versioned update framework primitives."""

from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
from pathlib import Path

from .exceptions import ChecksumValidationError, SecurityValidationError, UpdateError
from .models import UpdateApplicationEntry, UpdateManifest
from .path_utils import atomic_write_json, ensure_within_directory, read_json


def compare_semver(left: str, right: str) -> int:
    """Compare two simple semantic versions."""

    def parts(value: str) -> tuple[int, int, int]:
        core = value.split("-", 1)[0].split("+", 1)[0]
        major, minor, patch = core.split(".")
        return int(major), int(minor), int(patch)

    a = parts(left)
    b = parts(right)
    return (a > b) - (a < b)


class UpdateManager:
    """Checks, stages, verifies, and activates versioned releases."""

    def __init__(self, network_release_dir: Path | None, local_base_dir: Path, verify_sha256: bool = True) -> None:
        self.network_release_dir = network_release_dir
        self.local_base_dir = local_base_dir
        self.verify_sha256 = verify_sha256

    def network_available(self) -> bool:
        return bool(self.network_release_dir and self.network_release_dir.exists())

    def load_update_manifest(self, manifest_path: Path) -> UpdateManifest:
        data = read_json(manifest_path)
        apps = [
            UpdateApplicationEntry(
                id=str(item["id"]),
                version=str(item["version"]),
                relative_path=str(item["relative_path"]),
                sha256_manifest=str(item["sha256_manifest"]),
            )
            for item in data.get("applications", [])
        ]
        return UpdateManifest(
            schema_version=int(data["schema_version"]),
            platform_version=str(data["platform_version"]),
            published_at=str(data["published_at"]),
            applications=apps,
        )

    def sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def validate_checksum_file(self, root: Path, checksum_file: Path) -> None:
        """Validate a GNU-style checksum file under root."""

        for raw_line in checksum_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            expected, relative = line.split(maxsplit=1)
            target = ensure_within_directory(root / relative.lstrip("* "), root)
            if not target.exists() or self.sha256_file(target) != expected:
                raise ChecksumValidationError(f"Checksum failed for {relative}")

    def stage_release(self, source: Path, version: str) -> Path:
        """Copy to a private staging directory without deleting another update."""

        staging_root = self._version_path("staging", version).parent
        if not source.exists():
            raise UpdateError(f"Release source unavailable: {source}")
        staging_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f"{version}.", dir=staging_root))
        try:
            # Reject links/junctions that could import files outside the release.
            for path in source.rglob("*"):
                ensure_within_directory(path, source)
            shutil.copytree(source, staging, dirs_exist_ok=True)
        except Exception:
            shutil.rmtree(staging)
            raise
        return staging

    def activate_staged_release(self, staging: Path, version: str) -> Path:
        """Move a new version, then atomically select it, retaining old releases."""

        target = self._version_path("releases", version)
        staging_root = self._version_path("staging", version).parent
        try:
            staging = ensure_within_directory(staging, staging_root)
        except SecurityValidationError as exc:
            raise UpdateError("Release must come from the local staging directory") from exc
        if staging == staging_root or not staging.is_dir():
            raise UpdateError("A version directory inside local staging is required")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise UpdateError(f"Release {version} already exists; use a new version to preserve rollback")
        staging.rename(target)
        active = self.local_base_dir / "active_version.json"
        atomic_write_json(active, {"platform_version": version})
        return target

    def _version_path(self, directory: str, version: str) -> Path:
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?", version):
            raise UpdateError("Release version must be a safe semantic version")
        try:
            expected = self.local_base_dir.resolve() / directory / version
            resolved = ensure_within_directory(expected, self.local_base_dir)
            if resolved != expected:
                raise SecurityValidationError("Managed update directories cannot be links or junction aliases")
            return resolved
        except SecurityValidationError as exc:
            raise UpdateError("Release directory escapes its designated cache location") from exc
