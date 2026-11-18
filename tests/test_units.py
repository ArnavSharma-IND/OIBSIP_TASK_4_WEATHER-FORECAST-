"""Unit conversion and formatting tests."""

import pytest

from utils.weather_helpers import (
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    format_pressure,
    format_temperature,
    format_visibility,
    format_wind_speed,
)


class TestUnitConversions:
    """Test temperature conversions and unit calculations."""

    def test_celsius_to_fahrenheit_standard(self):
        assert celsius_to_fahrenheit(0.0) == 32.0
        assert celsius_to_fahrenheit(100.0) == 212.0
        assert celsius_to_fahrenheit(20.0) == 68.0

    def test_celsius_to_fahrenheit_boundary_values(self):
        # -40 is the crossover point where C == F
        assert celsius_to_fahrenheit(-40.0) == -40.0
        # Absolute zero approx -273.15 C -> -459.67 F
        assert abs(celsius_to_fahrenheit(-273.15) - (-459.7)) < 0.2

    def test_celsius_to_fahrenheit_decimals(self):
        assert celsius_to_fahrenheit(21.5) == 70.7
        assert celsius_to_fahrenheit(36.6) == 97.9

    def test_fahrenheit_to_celsius(self):
        assert fahrenheit_to_celsius(32.0) == 0.0
        assert fahrenheit_to_celsius(212.0) == 100.0
        assert fahrenheit_to_celsius(-40.0) == -40.0
        assert fahrenheit_to_celsius(68.0) == 20.0

    def test_format_temperature_celsius(self):
        assert format_temperature(21.4, unit="celsius", show_symbol=True) == "21°C"
        assert format_temperature(21.6, unit="celsius", show_symbol=True) == "22°C"
        assert format_temperature(0.0, unit="celsius", show_symbol=True) == "0°C"
        assert format_temperature(21.4, unit="celsius", show_symbol=False) == "21"

    def test_format_temperature_fahrenheit(self):
        # 20°C -> 68°F
        assert format_temperature(20.0, unit="fahrenheit", show_symbol=True) == "68°F"
        assert format_temperature(0.0, unit="fahrenheit", show_symbol=True) == "32°F"
        assert format_temperature(0.0, unit="fahrenheit", show_symbol=False) == "32"

    def test_format_wind_speed_metric(self):
        # 10 m/s -> 36 km/h
        result = format_wind_speed(10.0, unit="celsius")
        assert "36.0 km/h" in result
        assert "10.0 m/s" in result

    def test_format_wind_speed_imperial(self):
        # 10 m/s -> approx 22.4 mph
        result = format_wind_speed(10.0, unit="fahrenheit")
        assert "22.4 mph" in result

    def test_format_visibility_metric(self):
        assert format_visibility(10000, unit="celsius") == "10.0 km"
        assert format_visibility(500, unit="celsius") == "0.5 km"
        assert format_visibility(None, unit="celsius") == "N/A"

    def test_format_visibility_imperial(self):
        # 10,000 meters -> approx 6.2 miles
        result = format_visibility(10000, unit="fahrenheit")
        assert "6.2 mi" in result

    def test_format_pressure(self):
        assert format_pressure(1013) == "1013 hPa"
        assert format_pressure(None) == "N/A"
