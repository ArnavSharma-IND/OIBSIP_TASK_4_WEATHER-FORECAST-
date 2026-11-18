"""Weather API Service Layer for OpenWeatherMap integration.

Handles API request building, validation, timeout handling, error parsing,
response normalization, and integration with the cache layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import OWM_FORECAST_URL, OWM_WEATHER_URL, get_api_key
from services.cache_service import cache_service
from services.geocoding import GeocodingService
from utils.logger import app_logger
from utils.validators import validate_api_key, validate_location_input
from utils.weather_helpers import (
    extract_hourly_forecast,
    group_five_day_forecast,
)


@dataclass
class WeatherDataResult:
    """Encapsulates the outcome of a weather retrieval attempt."""

    success: bool
    error_message: str = ""
    error_code: str = ""  # e.g., "NOT_FOUND", "AUTH_ERROR", "TIMEOUT", "NETWORK_ERROR", "RATE_LIMIT"
    location_name: str = ""
    country: str = ""
    timezone_offset: int = 0
    current: Optional[Dict[str, Any]] = None
    hourly: Optional[List[Dict[str, Any]]] = None
    daily: Optional[List[Dict[str, Any]]] = None
    last_updated: float = 0.0
    from_cache: bool = False


class WeatherAPIService:
    """Production-grade service client for OpenWeatherMap API."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10) -> None:
        self.api_key = api_key if api_key is not None else get_api_key()
        self.timeout = timeout

    def set_api_key(self, key: str) -> None:
        """Update active API key."""
        self.api_key = key.strip()

    def fetch_weather(
        self,
        location_query: str,
        force_refresh: bool = False,
    ) -> WeatherDataResult:
        """Fetch current weather and 5-day forecast for a given location query.

        Args:
            location_query: City name, 'City, Country', or postal code
            force_refresh: If True, bypasses memory cache and hits API

        Returns:
            WeatherDataResult containing normalized weather data or error info.
        """
        # 1. Validate query input
        is_valid_query, query_err, parsed = validate_location_input(location_query)
        if not is_valid_query:
            return WeatherDataResult(
                success=False,
                error_message=query_err,
                error_code="VALIDATION_ERROR",
            )

        # 2. Validate API key
        active_key = self.api_key.strip() if self.api_key else get_api_key().strip()
        is_valid_key, key_err = validate_api_key(active_key)
        if not is_valid_key:
            return WeatherDataResult(
                success=False,
                error_message=key_err,
                error_code="MISSING_API_KEY",
            )

        cache_key = parsed["clean_query"].lower()

        # 3. Check cache if not forcing refresh
        if not force_refresh:
            cached_data = cache_service.get_weather(cache_key)
            if cached_data:
                app_logger.info("Serving weather for '%s' from cache", cache_key)
                return WeatherDataResult(
                    success=True,
                    location_name=cached_data["location_name"],
                    country=cached_data["country"],
                    timezone_offset=cached_data["timezone_offset"],
                    current=cached_data["current"],
                    hourly=cached_data["hourly"],
                    daily=cached_data["daily"],
                    last_updated=cached_data["last_updated"],
                    from_cache=True,
                )

        # 4. Prepare request parameters
        current_params: Dict[str, Any] = {
            "appid": active_key,
            "units": "metric",  # Always fetch metric Celsius for standard base
        }
        forecast_params: Dict[str, Any] = {
            "appid": active_key,
            "units": "metric",
        }

        # Handle ZIP / Postal code vs City
        if parsed.get("query_type") == "zip":
            # Attempt geocoding to lat/lon first for maximum accuracy across countries
            geo = GeocodingService.zip_geocode(
                parsed["zip_code"],
                parsed["country_code"],
                active_key,
                timeout=self.timeout,
            )
            if geo:
                current_params["lat"] = geo["lat"]
                current_params["lon"] = geo["lon"]
                forecast_params["lat"] = geo["lat"]
                forecast_params["lon"] = geo["lon"]
            else:
                zip_val = f"{parsed['zip_code']},{parsed['country_code']}" if parsed["country_code"] else parsed["zip_code"]
                current_params["zip"] = zip_val
                forecast_params["zip"] = zip_val
        else:
            current_params["q"] = parsed["clean_query"]
            forecast_params["q"] = parsed["clean_query"]

        # 5. Execute HTTP requests with robust error handling
        try:
            # A. Current Weather API call
            app_logger.info("Requesting current weather for: %s", parsed["clean_query"])
            curr_resp = requests.get(OWM_WEATHER_URL, params=current_params, timeout=self.timeout)
            curr_data, err_res = self._check_response(curr_resp, parsed["clean_query"])
            if err_res:
                return err_res

            # B. Forecast API call
            # If coordinates are available from current response, use them for forecast
            if "coord" in curr_data:
                forecast_params = {
                    "lat": curr_data["coord"]["lat"],
                    "lon": curr_data["coord"]["lon"],
                    "appid": active_key,
                    "units": "metric",
                }

            app_logger.info("Requesting 5-day forecast for: %s", parsed["clean_query"])
            fore_resp = requests.get(OWM_FORECAST_URL, params=forecast_params, timeout=self.timeout)
            fore_data, err_fore = self._check_response(fore_resp, parsed["clean_query"])
            if err_fore:
                return err_fore

            # 6. Normalize and process responses
            normalized = self._normalize_weather_data(curr_data, fore_data)

            # Store in cache
            cache_service.set_weather(cache_key, normalized)

            return WeatherDataResult(
                success=True,
                location_name=normalized["location_name"],
                country=normalized["country"],
                timezone_offset=normalized["timezone_offset"],
                current=normalized["current"],
                hourly=normalized["hourly"],
                daily=normalized["daily"],
                last_updated=normalized["last_updated"],
                from_cache=False,
            )

        except requests.exceptions.Timeout:
            app_logger.error("Weather API request timed out after %ds", self.timeout)
            return WeatherDataResult(
                success=False,
                error_message="The request timed out. Please check your internet connection and try again.",
                error_code="TIMEOUT",
            )
        except requests.exceptions.ConnectionError:
            app_logger.error("Network connection error connecting to weather service")
            return WeatherDataResult(
                success=False,
                error_message="Unable to connect to the weather service. Please check your network connection.",
                error_code="NETWORK_ERROR",
            )
        except requests.exceptions.RequestException as e:
            app_logger.error("Unexpected network request error: %s", e)
            return WeatherDataResult(
                success=False,
                error_message=f"Network error: {str(e)}",
                error_code="NETWORK_ERROR",
            )
        except Exception as e:
            app_logger.exception("Unexpected error processing weather data: %s", e)
            return WeatherDataResult(
                success=False,
                error_message="An unexpected error occurred while processing weather data.",
                error_code="UNKNOWN_ERROR",
            )

    def _check_response(
        self,
        response: requests.Response,
        query: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[WeatherDataResult]]:
        """Validate HTTP response and handle status codes."""
        status = response.status_code

        if status == 200:
            try:
                data = response.json()
                return data, None
            except Exception:
                return None, WeatherDataResult(
                    success=False,
                    error_message="Received an invalid JSON response from the weather service.",
                    error_code="INVALID_JSON",
                )

        if status == 404:
            app_logger.info("Location '%s' not found (404)", query)
            return None, WeatherDataResult(
                success=False,
                error_message=f"Location '{query}' was not found. Please verify spelling or try including country code (e.g. 'Paris, FR').",
                error_code="NOT_FOUND",
            )

        if status == 401:
            app_logger.error("Unauthorized (401): Invalid OpenWeatherMap API key")
            return None, WeatherDataResult(
                success=False,
                error_message=(
                    "Invalid or unactivated API key (401).\n"
                    "• Note for new accounts: OpenWeatherMap requires 10 to 60 minutes to activate new keys.\n"
                    "• Please verify your email address if you recently registered.\n"
                    "• Verify the key in Settings or your .env file."
                ),
                error_code="AUTH_ERROR",
            )

        if status == 429:
            app_logger.warning("Rate limit exceeded (429)")
            return None, WeatherDataResult(
                success=False,
                error_message="API rate limit exceeded. OpenWeatherMap free tier allows 60 calls/minute. Please wait a moment and try again.",
                error_code="RATE_LIMIT",
            )

        # Other HTTP errors
        msg = f"Weather service returned error code {status}."
        try:
            body = response.json()
            if "message" in body:
                msg = f"{msg} Details: {body['message']}"
        except Exception:
            pass

        return None, WeatherDataResult(
            success=False,
            error_message=msg,
            error_code=f"HTTP_{status}",
        )

    def _normalize_weather_data(
        self,
        curr: Dict[str, Any],
        fore: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize raw OpenWeatherMap responses into structured weather models."""
        # Location info
        location_name = curr.get("name", "Unknown Location")
        sys_info = curr.get("sys", {})
        country = sys_info.get("country", "")
        timezone_offset = int(curr.get("timezone", 0))

        # Current weather details
        main_info = curr.get("main", {})
        weather_list = curr.get("weather", [])
        w_curr = weather_list[0] if weather_list else {}
        wind_info = curr.get("wind", {})

        temp_c = float(main_info.get("temp", 0.0))
        feels_c = float(main_info.get("feels_like", temp_c))
        temp_min_c = float(main_info.get("temp_min", temp_c))
        temp_max_c = float(main_info.get("temp_max", temp_c))
        humidity = int(main_info.get("humidity", 0))
        pressure = int(main_info.get("pressure", 1013))
        visibility = curr.get("visibility")  # meters

        sunrise = sys_info.get("sunrise", 0)
        sunset = sys_info.get("sunset", 0)

        current_dict = {
            "temp_c": temp_c,
            "feels_c": feels_c,
            "temp_min_c": temp_min_c,
            "temp_max_c": temp_max_c,
            "humidity": humidity,
            "pressure": pressure,
            "visibility_m": visibility,
            "wind_speed_mps": float(wind_info.get("speed", 0.0)),
            "wind_deg": wind_info.get("deg", 0),
            "wind_gust_mps": float(wind_info.get("gust", 0.0)) if "gust" in wind_info else None,
            "condition": w_curr.get("main", "Clear"),
            "description": w_curr.get("description", "clear sky").title(),
            "icon": w_curr.get("icon", "01d"),
            "sunrise": sunrise,
            "sunset": sunset,
            "calc_time": curr.get("dt", int(time.time())),
        }

        # Forecast list
        raw_forecast_list = fore.get("list", [])
        # Extract hourly (3-hour intervals)
        hourly_list = extract_hourly_forecast(
            raw_forecast_list,
            timezone_offset_seconds=timezone_offset,
            max_intervals=8,
        )

        # Extract 5-day daily summaries
        daily_list = group_five_day_forecast(
            raw_forecast_list,
            timezone_offset_seconds=timezone_offset,
        )

        return {
            "location_name": location_name,
            "country": country,
            "timezone_offset": timezone_offset,
            "current": current_dict,
            "hourly": hourly_list,
            "daily": daily_list,
            "last_updated": time.time(),
        }
