"""Logging configuration for Weather & Forecast application.

Provides sanitized logging to prevent exposing API keys or sensitive user data.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from config import CACHE_DIR

LOG_FILE = CACHE_DIR / "application.log"


class SensitiveDataFilter(logging.Filter):
    """Filter to redact potential API keys or query tokens from logs."""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.msg)
        # Redact common pattern for appid or api key
        import re
        msg = re.sub(r"(appid|key)=([a-zA-Z0-9_-]{16,})", r"\1=[REDACTED]", msg, flags=re.IGNORECASE)
        record.msg = msg
        return True


def setup_logger(name: str = "WeatherApp", level: int = logging.INFO) -> logging.Logger:
    """Set up and configure application logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sensitive_filter = SensitiveDataFilter()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)
    except Exception:
        # Fallback if file logging fails
        pass

    return logger


# Global logger instance
app_logger = setup_logger()
