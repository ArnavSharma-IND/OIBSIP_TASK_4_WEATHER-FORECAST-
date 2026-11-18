"""Input validation tests for location queries and API keys."""

import pytest

from utils.validators import validate_api_key, validate_location_input


class TestValidators:
    """Test user input validation rules."""

    def test_empty_location_rejected(self):
        valid, msg, _ = validate_location_input("")
        assert not valid
        assert "cannot be empty" in msg

        valid, msg, _ = validate_location_input("   ")
        assert not valid
        assert "cannot be empty" in msg

        valid, msg, _ = validate_location_input(None)
        assert not valid

    def test_short_location_rejected(self):
        valid, msg, _ = validate_location_input("a")
        assert not valid
        assert "too short" in msg

    def test_invalid_characters_rejected(self):
        invalid_inputs = ["London<script>", "Paris;DROP TABLE", "Tokyo{test}", "Berlin$"]
        for inp in invalid_inputs:
            valid, msg, _ = validate_location_input(inp)
            assert not valid
            assert "invalid characters" in msg

    def test_valid_city_names(self):
        valid, msg, parsed = validate_location_input("London")
        assert valid
        assert parsed["query_type"] == "city"
        assert parsed["city_name"] == "London"

        valid, msg, parsed = validate_location_input("New York, US")
        assert valid
        assert parsed["query_type"] == "city"
        assert parsed["country_code"] == "US"

        valid, msg, parsed = validate_location_input("São Paulo, BR")
        assert valid
        assert parsed["query_type"] == "city"
        assert parsed["country_code"] == "BR"

    def test_whitespace_trimmed(self):
        valid, msg, parsed = validate_location_input("   Tokyo   ")
        assert valid
        assert parsed["clean_query"] == "Tokyo"

    def test_valid_zip_codes(self):
        # US ZIP code
        valid, msg, parsed = validate_location_input("90210")
        assert valid
        assert parsed["query_type"] == "zip"
        assert parsed["zip_code"] == "90210"

        # US ZIP with country
        valid, msg, parsed = validate_location_input("90210, US")
        assert valid
        assert parsed["query_type"] == "zip"
        assert parsed["zip_code"] == "90210"
        assert parsed["country_code"] == "US"

        # Indian PIN code
        valid, msg, parsed = validate_location_input("110001, IN")
        assert valid
        assert parsed["query_type"] == "zip"
        assert parsed["zip_code"] == "110001"
        assert parsed["country_code"] == "IN"

    def test_validate_api_key(self):
        # Empty
        valid, msg = validate_api_key("")
        assert not valid
        assert "missing" in msg

        valid, msg = validate_api_key(None)
        assert not valid

        # Too short
        valid, msg = validate_api_key("short_key")
        assert not valid
        assert "too short" in msg

        # Valid mock key (32 chars)
        valid, msg = validate_api_key("1234567890abcdef1234567890abcdef")
        assert valid
        assert msg == ""
