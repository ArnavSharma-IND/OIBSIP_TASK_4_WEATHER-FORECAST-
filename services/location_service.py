"""Location service providing IP-based geolocation with user privacy controls."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import requests

from config import IPAPI_FALLBACK_URL, IPINFO_URL
from utils.logger import app_logger


class LocationService:
    """Provides approximate geolocation based on public IP address."""

    @staticmethod
    def detect_approximate_location(timeout: int = 6) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Detect approximate location using ipinfo.io with fallback to ipapi.co.

        Returns:
            (success: bool, message: str, location_data: Optional[Dict])
        """
        # 1. Primary: ipinfo.io
        try:
            response = requests.get(IPINFO_URL, headers={"Accept": "application/json"}, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                city = data.get("city", "").strip()
                country = data.get("country", "").strip()
                region = data.get("region", "").strip()
                loc = data.get("loc", "").strip()  # "lat,lon"

                lat = 0.0
                lon = 0.0
                if loc and "," in loc:
                    try:
                        parts = loc.split(",")
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                    except ValueError:
                        pass

                if city:
                    return True, "Approximate location detected successfully via IP.", {
                        "city": city,
                        "region": region,
                        "country": country,
                        "lat": lat,
                        "lon": lon,
                        "query_string": f"{city}, {country}" if country else city,
                    }
        except requests.exceptions.RequestException as e:
            app_logger.warning("ipinfo.io lookup failed: %s, attempting fallback...", e)

        # 2. Fallback: ipapi.co
        try:
            response = requests.get(IPAPI_FALLBACK_URL, headers={"User-Agent": "WeatherApp/1.0"}, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                city = data.get("city", "").strip()
                country = data.get("country_name", data.get("country", "")).strip()
                region = data.get("region", "").strip()
                lat = float(data.get("latitude", 0.0))
                lon = float(data.get("longitude", 0.0))

                if city:
                    return True, "Approximate location detected successfully via IP fallback.", {
                        "city": city,
                        "region": region,
                        "country": country,
                        "lat": lat,
                        "lon": lon,
                        "query_string": f"{city}, {country}" if country else city,
                    }
        except requests.exceptions.RequestException as e:
            app_logger.warning("ipapi.co fallback failed: %s", e)

        return False, "Could not detect location automatically via IP. Please enter your city manually.", None
