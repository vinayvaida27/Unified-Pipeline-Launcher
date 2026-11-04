"""Custom exceptions for the launcher."""


class LauncherError(Exception):
    """Base class for launcher errors."""


class ConfigurationError(LauncherError):
    """Raised when platform configuration is invalid."""


class ManifestValidationError(LauncherError):
    """Raised when an application manifest is invalid."""


class RuntimeNotFoundError(LauncherError):
    """Raised when no approved Python runtime is available."""


class RuntimeValidationError(LauncherError):
    """Raised when a Python runtime cannot satisfy launcher requirements."""


class RuntimeDownloadError(LauncherError):
    """Raised when the pinned official Python runtime cannot be downloaded."""


class EnvironmentCreationError(LauncherError):
    """Raised when a virtual environment cannot be created."""


class DependencyInstallationError(LauncherError):
    """Raised when application dependencies cannot be installed."""


class ApplicationStartError(LauncherError):
    """Raised when a Streamlit application cannot be started."""


class ApplicationHealthCheckError(LauncherError):
    """Raised when a launched application does not become healthy."""


class ApplicationStopError(LauncherError):
    """Raised when an application cannot be stopped."""


class UpdateError(LauncherError):
    """Raised when platform update processing fails."""


class ChecksumValidationError(UpdateError):
    """Raised when checksum verification fails."""


class SecurityValidationError(LauncherError):
    """Raised when untrusted paths or data are rejected."""
