"""Application Configuration Module for Weather & Forecast Desktop Application.

Handles paths, environment variables, API endpoints, and persistent settings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
ICONS_CACHE_DIR = CACHE_DIR / "icons"
SETTINGS_FILE = CACHE_DIR / "settings.json"
FAVOURITES_FILE = CACHE_DIR / "favourites.json"

# Ensure runtime directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ICONS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# App Metadata
APP_NAME = "Weather & Forecast"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Arnav Sharma"

# OpenWeatherMap API Endpoints
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5"
OWM_WEATHER_URL = f"{OWM_BASE_URL}/weather"
OWM_FORECAST_URL = f"{OWM_BASE_URL}/forecast"
OWM_GEO_DIRECT_URL = "https://api.openweathermap.org/geo/1.0/direct"
OWM_GEO_ZIP_URL = "https://api.openweathermap.org/geo/1.0/zip"
OWM_ICON_URL_TEMPLATE = "https://openweathermap.org/img/wn/{icon}@2x.png"

# IP Geolocation Endpoints
IPINFO_URL = "https://ipinfo.io/json"
IPAPI_FALLBACK_URL = "https://ipapi.co/json/"

# Default Settings
DEFAULT_SETTINGS: Dict[str, Any] = {
    "api_key": os.getenv("OPENWEATHER_API_KEY", "").strip(),
    "units": os.getenv("DEFAULT_UNITS", "celsius").strip().lower(),
    "theme": os.getenv("DEFAULT_THEME", "light").strip().lower(),
    "default_location": os.getenv("DEFAULT_LOCATION", "London").strip(),
    "timeout_seconds": int(os.getenv("API_TIMEOUT_SECONDS", "10")),
    "auto_detect_location_on_startup": False,
    "cache_ttl_minutes": 10,
}


def clean_api_key(raw_key: Optional[str]) -> str:
    """Sanitize API key by stripping whitespace and surrounding quotes."""
    if not raw_key:
        return ""
    return str(raw_key).strip().strip("'\"").strip()


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file with fallback to defaults and environment."""
    settings = dict(DEFAULT_SETTINGS)

    # Re-read environment in case it was updated
    env_key = clean_api_key(os.getenv("OPENWEATHER_API_KEY", ""))
    if env_key:
        settings["api_key"] = env_key

    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    settings.update(saved)
        except Exception:
            # Corrupted file: return current settings
            pass

    # Ensure api_key is sanitized
    settings["api_key"] = clean_api_key(settings.get("api_key", ""))

    # Ensure api_key from env has precedence if file had empty
    if not settings.get("api_key") and env_key:
        settings["api_key"] = env_key

    # Validate units
    if settings.get("units") not in ("celsius", "fahrenheit"):
        settings["units"] = "celsius"

    # Validate theme
    if settings.get("theme") not in ("light", "dark"):
        settings["theme"] = "light"

    return settings


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save user settings to JSON file and sync API key to .env."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        merged = load_settings()
        merged.update(settings)
        if "api_key" in merged:
            merged["api_key"] = clean_api_key(merged["api_key"])

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)

        # Sync API key to .env if present
        if merged.get("api_key"):
            env_path = BASE_DIR / ".env"
            try:
                env_lines = []
                key_written = False
                if env_path.exists():
                    with open(env_path, "r", encoding="utf-8") as ef:
                        for line in ef:
                            if line.startswith("OPENWEATHER_API_KEY="):
                                env_lines.append(f"OPENWEATHER_API_KEY={merged['api_key']}\n")
                                key_written = True
                            else:
                                env_lines.append(line)
                if not key_written:
                    env_lines.append(f"OPENWEATHER_API_KEY={merged['api_key']}\n")
                with open(env_path, "w", encoding="utf-8") as ef:
                    ef.writelines(env_lines)
            except Exception:
                pass

        return True
    except Exception:
        return False


def get_api_key() -> str:
    """Get active OpenWeatherMap API key."""
    settings = load_settings()
    return settings.get("api_key", "").strip()
