"""Tests for forecast extraction, daily grouping, timezone handling, and weather insights."""

from datetime import datetime, timezone

import pytest

from utils.weather_helpers import (
    extract_hourly_forecast,
    format_date_local,
    format_time_local,
    generate_weather_insights,
    get_local_datetime,
    group_five_day_forecast,
)


class TestForecastProcessing:
    """Test forecast interval extraction and daily aggregation."""

    @pytest.fixture
    def sample_forecast_list(self):
        """Generate sample 3-hour forecast intervals."""
        # Base timestamp: 2026-11-18 00:00:00 UTC
        base_dt = 1795046400
        intervals = []
        # Create 16 intervals (2 full days)
        for i in range(16):
            dt = base_dt + (i * 3 * 3600)
            # Vary temperatures between 10 and 22 C
            temp = 15.0 + (i % 8)
            intervals.append({
                "dt": dt,
                "main": {
                    "temp": temp,
                    "feels_like": temp + 1.0,
                    "temp_min": temp - 2.0,
                    "temp_max": temp + 2.0,
                    "humidity": 60 + i,
                    "pressure": 1015,
                },
                "weather": [{
                    "main": "Rain" if i % 4 == 0 else "Clouds",
                    "description": "light rain" if i % 4 == 0 else "scattered clouds",
                    "icon": "10d" if i % 4 == 0 else "03d",
                }],
                "pop": 0.6 if i % 4 == 0 else 0.1,
            })
        return intervals

    def test_extract_hourly_forecast(self, sample_forecast_list):
        hourly = extract_hourly_forecast(sample_forecast_list, timezone_offset_seconds=0, max_intervals=6)
        assert len(hourly) == 6

        first = hourly[0]
        assert "time_display" in first
        assert "temp_c" in first
        assert "condition" in first
        assert "icon" in first
        assert "pop_percent" in first
        assert first["temp_c"] == 15.0
        assert first["pop_percent"] == 60

    def test_timezone_offset_handling(self):
        # 2026-11-18 12:00:00 UTC (dt = 1795089600)
        utc_timestamp = 1795089600

        # In UTC (offset 0), time should be 12:00
        time_utc = format_time_local(utc_timestamp, timezone_offset_seconds=0)
        assert time_utc == "12:00"

        # In Tokyo (UTC +9 = +32400 seconds), time should be 21:00
        time_tokyo = format_time_local(utc_timestamp, timezone_offset_seconds=32400)
        assert time_tokyo == "21:00"

        # In New York (UTC -5 = -18000 seconds), time should be 07:00
        time_ny = format_time_local(utc_timestamp, timezone_offset_seconds=-18000)
        assert time_ny == "07:00"

    def test_group_five_day_forecast(self, sample_forecast_list):
        daily = group_five_day_forecast(sample_forecast_list, timezone_offset_seconds=0)
        # We provided 2 days worth of intervals
        assert len(daily) == 2

        day1 = daily[0]
        assert "day_name" in day1
        assert "formatted_date" in day1
        assert "temp_min_c" in day1
        assert "temp_max_c" in day1
        assert day1["temp_min_c"] <= day1["temp_max_c"]
        assert day1["max_pop_percent"] == 60
        assert "icon" in day1

    def test_group_forecast_missing_fields(self):
        # Gracefully handle sparse or missing entries
        sparse_intervals = [
            {"dt": 1795046400, "main": {}},
            {"dt": 1795057200, "main": {"temp": 18.0}, "weather": []},
        ]
        daily = group_five_day_forecast(sparse_intervals, timezone_offset_seconds=0)
        assert len(daily) == 1
        assert daily[0]["temp_max_c"] >= 0.0

    def test_generate_weather_insights(self):
        # Raining currently
        current = {
            "temp_c": 14.0,
            "feels_c": 14.0,
            "humidity": 88,
            "wind_speed_mps": 4.0,
            "condition": "Rain",
            "description": "light rain",
        }
        insights = generate_weather_insights(current)
        assert any("umbrella" in ins.lower() for ins in insights)

        # High wind
        current_windy = {
            "temp_c": 18.0,
            "feels_c": 18.0,
            "humidity": 50,
            "wind_speed_mps": 12.5,
            "condition": "Clouds",
            "description": "overcast clouds",
        }
        insights_windy = generate_weather_insights(current_windy)
        assert any("winds" in ins.lower() for ins in insights_windy)

        # Sub-zero freeze
        current_freeze = {
            "temp_c": -3.0,
            "feels_c": -8.0,
            "humidity": 65,
            "wind_speed_mps": 5.0,
            "condition": "Snow",
            "description": "light snow",
        }
        insights_freeze = generate_weather_insights(current_freeze)
        assert any("freezing" in ins.lower() for ins in insights_freeze)
