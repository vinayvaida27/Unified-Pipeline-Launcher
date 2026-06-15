"""Logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .models import LoggingConfig


def configure_logging(cache_dir: Path, config: LoggingConfig) -> Path:
    """Configure rotating launcher logs and return the log path."""

    log_dir = cache_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "launcher.log"
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.level.upper(), logging.INFO))
    root.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = RotatingFileHandler(
        log_path,
        maxBytes=config.maximum_file_size_mb * 1024 * 1024,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)
    return log_path
