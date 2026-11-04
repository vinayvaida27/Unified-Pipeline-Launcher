"""Launcher constants."""

from pathlib import Path

SUPPORTED_SCHEMA_VERSION = 1
SUPPORTED_APP_TYPES = {"streamlit"}
SUPPORTED_PYTHON_MIN = (3, 11)
SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 13)
DEFAULT_ADDRESS = "127.0.0.1"
HEALTH_PATH = "/_stcore/health"
STATE_SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parent.parent
