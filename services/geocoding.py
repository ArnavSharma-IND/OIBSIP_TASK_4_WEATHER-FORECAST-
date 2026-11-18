"""Geocoding service for resolving city names and postal codes to coordinates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from config import OWM_GEO_DIRECT_URL, OWM_GEO_ZIP_URL
from utils.logger import app_logger


class GeocodingService:
    """Provides direct and postal code geocoding via OpenWeatherMap Geocoding API."""

    @staticmethod
    def direct_geocode(
        query: str,
        api_key: str,
        limit: int = 1,
        timeout: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """Resolve a city or place name into coordinates.

        Args:
            query: City name, e.g., "London" or "Paris, FR"
            api_key: OpenWeatherMap API key
            limit: Maximum locations to retrieve
            timeout: Request timeout in seconds
        """
        if not query or not api_key:
            return None

        params = {
            "q": query.strip(),
            "limit": limit,
            "appid": api_key.strip(),
        }

        try:
            response = requests.get(OWM_GEO_DIRECT_URL, params=params, timeout=timeout)
            if response.status_code == 200:
                results = response.json()
                if isinstance(results, list) and len(results) > 0:
                    first = results[0]
                    return {
                        "name": first.get("name", query),
                        "lat": float(first.get("lat", 0.0)),
                        "lon": float(first.get("lon", 0.0)),
                        "country": first.get("country", ""),
                        "state": first.get("state", ""),
                    }
            elif response.status_code == 401:
                app_logger.error("Geocoding failed: Invalid API key")
            elif response.status_code == 404:
                app_logger.info("Geocoding: Location '%s' not found", query)
            else:
                app_logger.warning("Geocoding failed with status %d", response.status_code)
        except requests.exceptions.RequestException as e:
            app_logger.error("Geocoding request exception for '%s': %s", query, e)

        return None

    @staticmethod
    def zip_geocode(
        zip_code: str,
        country_code: str,
        api_key: str,
        timeout: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """Resolve postal/ZIP code to coordinates.

        Args:
            zip_code: ZIP or Postal code, e.g. "90210" or "SW1A 1AA"
            country_code: 2-letter ISO country code (default 'US' if empty)
            api_key: OpenWeatherMap API key
            timeout: Request timeout in seconds
        """
        if not zip_code or not api_key:
            return None

        clean_zip = zip_code.strip()
        country = country_code.strip().upper() if country_code else "US"
        zip_param = f"{clean_zip},{country}"

        params = {
            "zip": zip_param,
            "appid": api_key.strip(),
        }

        try:
            response = requests.get(OWM_GEO_ZIP_URL, params=params, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": data.get("name", zip_code),
                    "lat": float(data.get("lat", 0.0)),
                    "lon": float(data.get("lon", 0.0)),
                    "country": data.get("country", country),
                    "zip": data.get("zip", zip_code),
                }
            elif response.status_code == 401:
                app_logger.error("ZIP Geocoding failed: Invalid API key")
            elif response.status_code == 404:
                app_logger.info("ZIP Geocoding: Postal code '%s' not found", zip_param)
        except requests.exceptions.RequestException as e:
            app_logger.error("ZIP Geocoding request exception: %s", e)

        return None
