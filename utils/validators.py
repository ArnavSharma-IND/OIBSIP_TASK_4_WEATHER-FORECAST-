"""Validation helpers for user inputs, location queries, and API parameters."""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple


def validate_location_input(raw_input: Optional[str]) -> Tuple[bool, str, Dict[str, str]]:
    """Validate and normalize user location input.

    Returns:
        (is_valid, error_message, parsed_data)
        where parsed_data contains:
          - "clean_query": trimmed and normalized query
          - "query_type": "zip" or "city"
          - "zip_code": extracted zip code if query_type == "zip"
          - "country_code": optional 2-letter ISO country code if present
          - "city_name": extracted city name if query_type == "city"
    """
    if raw_input is None:
        return False, "Location cannot be empty. Please enter a city or postal code.", {}

    trimmed = raw_input.strip()

    if not trimmed:
        return False, "Location cannot be empty. Please enter a city or postal code.", {}

    if len(trimmed) < 2:
        return False, "Location query is too short. Please enter at least 2 characters.", {}

    if len(trimmed) > 100:
        return False, "Location query is too long. Please enter a valid location.", {}

    # Disallow invalid symbols like < > $ ; { } [ ]
    if re.search(r"[<>{}\[\];$\\]", trimmed):
        return False, "Location contains invalid characters. Please use letters, numbers, commas, or hyphens.", {}

    parsed: Dict[str, str] = {
        "clean_query": trimmed,
        "query_type": "city",
        "zip_code": "",
        "country_code": "",
        "city_name": trimmed,
    }

    # Check if query is ZIP/Postal code format
    # Examples: "90210", "90210, US", "90210,US", "SW1A 1AA, GB", "110001, IN"
    # Or pure numeric/alphanumeric postal code with optional country
    zip_pattern = r"^([A-Za-z0-9\s\-]{3,10})(?:,\s*([A-Za-z]{2}))?$"
    zip_match = re.match(zip_pattern, trimmed)

    # If first token contains digits or fits typical postal code structure
    if zip_match:
        postal_part = zip_match.group(1).strip()
        country_part = (zip_match.group(2) or "").strip().upper()
        # Check if postal_part has at least one digit, or is a known postal style
        has_digit = any(c.isdigit() for c in postal_part)
        if has_digit or (country_part and len(postal_part) <= 8 and not " " in postal_part):
            parsed["query_type"] = "zip"
            parsed["zip_code"] = postal_part
            parsed["country_code"] = country_part
            if country_part:
                parsed["clean_query"] = f"{postal_part},{country_part}"
            else:
                parsed["clean_query"] = postal_part
            return True, "", parsed

    # Regular city or city, country
    # Examples: "London", "London, UK", "New York, US", "San Francisco, CA, US"
    parts = [p.strip() for p in trimmed.split(",") if p.strip()]
    if parts:
        parsed["city_name"] = parts[0]
        if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isalpha():
            parsed["country_code"] = parts[-1].upper()
            parsed["clean_query"] = f"{', '.join(parts[:-1])}, {parts[-1].upper()}"

    return True, "", parsed


def validate_api_key(api_key: Optional[str]) -> Tuple[bool, str]:
    """Validate OpenWeatherMap API key format (typically 32 hex characters)."""
    if not api_key or not api_key.strip():
        return False, "OpenWeatherMap API key is missing. Please set it in Settings or your .env file."

    cleaned = api_key.strip()
    if len(cleaned) < 16:
        return False, "API key appears to be invalid or too short. OpenWeatherMap keys are typically 32 characters."

    return True, ""
