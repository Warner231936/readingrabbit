"""Logging helpers for ReadingRabbit."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOGGER_NAME = "readingrabbit"


def setup_logging(log_path: Optional[str], log_level: str = "INFO") -> logging.Logger:
    """Configure and return the shared application logger."""

    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if log_path:
        path = Path(log_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            path,
            maxBytes=1_048_576,
            backupCount=3,
            encoding="utf-8",
        )
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    """Return the shared ReadingRabbit logger."""

    return logging.getLogger(_LOGGER_NAME)
