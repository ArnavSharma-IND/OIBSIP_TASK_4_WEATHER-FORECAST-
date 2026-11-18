"""Miscellaneous helper functions for the Weather & Forecast application."""

from __future__ import annotations

import os
import sys
from typing import Any, Optional


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller bundle.

    PyInstaller creates a temp folder and stores path in _MEIPASS.
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback."""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int with default fallback."""
    try:
        if value is None:
            return default
        return int(round(float(value)))
    except (ValueError, TypeError):
        return default
