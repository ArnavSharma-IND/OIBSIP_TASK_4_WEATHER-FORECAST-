"""Automated API integration tests with mocked HTTP responses."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from services.cache_service import cache_service
from services.weather_api import WeatherAPIService, WeatherDataResult


class TestWeatherAPIService:
    """Test suite for WeatherAPIService verifying robust error handling."""

    @pytest.fixture
    def service(self):
        # Clear cache before tests
        cache_service.clear_weather_cache()
        return WeatherAPIService(api_key="mock_valid_32char_api_key_12345678", timeout=5)

    @pytest.fixture
    def mock_current_success_json(self):
        return {
            "coord": {"lon": -0.1257, "lat": 51.5085},
            "weather": [
                {
                    "id": 721,
                    "main": "Haze",
                    "description": "haze",
                    "icon": "50d",
                }
            ],
            "base": "stations",
            "main": {
                "temp": 8.26,
                "feels_like": 8.26,
                "temp_min": 7.53,
                "temp_max": 8.89,
                "pressure": 1026,
                "humidity": 95,
                "sea_level": 1026,
                "grnd_level": 1021,
            },
            "visibility": 2900,
            "wind": {"speed": 0, "deg": 0},
            "clouds": {"all": 100},
            "dt": 1745735677,
            "sys": {
                "type": 1,
                "id": 1414,
                "country": "GB",
                "sunrise": 1745728782,
                "sunset": 1745781377,
            },
            "timezone": 3600,
            "id": 2643743,
            "name": "London",
            "cod": 200,
        }

    @pytest.fixture
    def mock_forecast_success_json(self):
        return {
            "city": {"name": "London", "country": "GB", "timezone": 0},
            "list": [
                {
                    "dt": 1700020000 + i * 10800,
                    "main": {
                        "temp": 18.0 + (i % 3),
                        "feels_like": 17.5,
                        "temp_min": 16.0,
                        "temp_max": 20.0,
                        "humidity": 70,
                        "pressure": 1014,
                    },
                    "weather": [{"main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
                    "pop": 0.2,
                }
                for i in range(8)
            ],
        }

    @patch("requests.get")
    def test_successful_weather_fetch(
        self,
        mock_get,
        service,
        mock_current_success_json,
        mock_forecast_success_json,
    ):
        """Test successful weather and forecast response."""
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = mock_current_success_json

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = mock_forecast_success_json

        mock_get.side_effect = [resp1, resp2]

        result = service.fetch_weather("London")

        assert result.success is True
        assert result.location_name == "London"
        assert result.country == "GB"
        assert result.current["temp_c"] == 8.26
        assert result.current["humidity"] == 95
        assert result.current["condition"] == "Haze"
        assert result.current["icon"] == "50d"
        assert result.timezone_offset == 3600
        assert len(result.hourly) > 0
        assert len(result.daily) > 0

    @patch("requests.get")
    def test_city_not_found_404(self, mock_get, service):
        """Test 404 response handling."""
        resp = MagicMock()
        resp.status_code = 404
        resp.json.return_value = {"cod": "404", "message": "city not found"}
        mock_get.return_value = resp

        result = service.fetch_weather("NonExistentCity123")

        assert result.success is False
        assert result.error_code == "NOT_FOUND"
        assert "not found" in result.error_message.lower()

    @patch("requests.get")
    def test_invalid_api_key_401(self, mock_get, service):
        """Test 401 Unauthorized handling."""
        resp = MagicMock()
        resp.status_code = 401
        resp.json.return_value = {"cod": 401, "message": "Invalid API key"}
        mock_get.return_value = resp

        result = service.fetch_weather("London")

        assert result.success is False
        assert result.error_code == "AUTH_ERROR"
        assert "api key" in result.error_message.lower()

    @patch("requests.get")
    def test_rate_limit_429(self, mock_get, service):
        """Test 429 Too Many Requests handling."""
        resp = MagicMock()
        resp.status_code = 429
        resp.json.return_value = {"cod": 429, "message": "Rate limit exceeded"}
        mock_get.return_value = resp

        result = service.fetch_weather("London")

        assert result.success is False
        assert result.error_code == "RATE_LIMIT"
        assert "rate limit" in result.error_message.lower()

    @patch("requests.get")
    def test_request_timeout(self, mock_get, service):
        """Test network timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = service.fetch_weather("London")

        assert result.success is False
        assert result.error_code == "TIMEOUT"
        assert "timed out" in result.error_message.lower()

    @patch("requests.get")
    def test_connection_error(self, mock_get, service):
        """Test network disconnection handling."""
        mock_get.side_effect = requests.exceptions.ConnectionError("DNS failure")

        result = service.fetch_weather("London")

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"
        assert "unable to connect" in result.error_message.lower()

    @patch("requests.get")
    def test_invalid_json_response(self, mock_get, service):
        """Test corrupted or invalid JSON response handling."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = resp

        result = service.fetch_weather("London")

        assert result.success is False
        assert result.error_code == "INVALID_JSON"

    def test_missing_api_key_validation(self):
        """Test validation error when API key is missing."""
        service = WeatherAPIService(api_key="", timeout=5)
        # Pass a mocked empty config
        with patch("services.weather_api.get_api_key", return_value=""):
            result = service.fetch_weather("London")
            assert result.success is False
            assert result.error_code == "MISSING_API_KEY"

    @patch("requests.get")
    def test_cache_hit_and_force_refresh(
        self,
        mock_get,
        service,
        mock_current_success_json,
        mock_forecast_success_json,
    ):
        """Test that repeated requests use cache unless forced."""
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = mock_current_success_json

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = mock_forecast_success_json

        mock_get.side_effect = [resp1, resp2, resp1, resp2]

        # First fetch: hits API
        res1 = service.fetch_weather("London")
        assert res1.success is True
        assert res1.from_cache is False
        assert mock_get.call_count == 2

        # Second fetch: hits memory cache
        res2 = service.fetch_weather("London")
        assert res2.success is True
        assert res2.from_cache is True
        assert mock_get.call_count == 2  # No new requests!

        # Third fetch with force_refresh: bypasses cache
        res3 = service.fetch_weather("London", force_refresh=True)
        assert res3.success is True
        assert res3.from_cache is False
        assert mock_get.call_count == 4  # New request made
