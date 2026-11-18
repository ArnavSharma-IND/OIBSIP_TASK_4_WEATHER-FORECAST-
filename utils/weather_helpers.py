"""Weather data helpers for unit conversions, timestamp formatting,
forecast aggregation, and analytical insights.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit using exact formula (°C * 9/5) + 32."""
    return round((celsius * 9.0 / 5.0) + 32.0, 1)


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius using exact formula (°F - 32) * 5/9."""
    return round((fahrenheit - 32.0) * 5.0 / 9.0, 1)


def format_temperature(temp_celsius: float, unit: str = "celsius", show_symbol: bool = True) -> str:
    """Format temperature in Celsius or Fahrenheit with symbol."""
    unit_lower = unit.lower()
    if unit_lower == "fahrenheit":
        val = celsius_to_fahrenheit(temp_celsius)
        rounded = int(round(val))
        return f"{rounded}°F" if show_symbol else f"{rounded}"
    else:
        rounded = int(round(temp_celsius))
        return f"{rounded}°C" if show_symbol else f"{rounded}"


def format_wind_speed(speed_mps: float, unit: str = "celsius") -> str:
    """Format wind speed based on selected unit preference.

    Metric: m/s and km/h
    Imperial (when unit is fahrenheit): mph
    """
    if unit.lower() == "fahrenheit":
        mph = speed_mps * 2.23694
        return f"{mph:.1f} mph"
    kmh = speed_mps * 3.6
    return f"{kmh:.1f} km/h ({speed_mps:.1f} m/s)"


def format_visibility(visibility_meters: Optional[int], unit: str = "celsius") -> str:
    """Format visibility in kilometers or miles."""
    if visibility_meters is None:
        return "N/A"
    if unit.lower() == "fahrenheit":
        miles = visibility_meters * 0.000621371
        return f"{miles:.1f} mi"
    km = visibility_meters / 1000.0
    return f"{km:.1f} km"


def format_pressure(pressure_hpa: Optional[int]) -> str:
    """Format atmospheric pressure in hPa."""
    if pressure_hpa is None:
        return "N/A"
    return f"{pressure_hpa} hPa"


def get_local_datetime(unix_timestamp: int, timezone_offset_seconds: int = 0) -> datetime:
    """Convert a UTC Unix timestamp to a localized naive datetime representing
    the target location's local time, respecting its timezone offset.
    """
    utc_dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    local_dt = utc_dt + timedelta(seconds=timezone_offset_seconds)
    # Return as naive datetime representing the wall-clock time in target location
    return local_dt.replace(tzinfo=None)


def format_time_local(unix_timestamp: int, timezone_offset_seconds: int = 0, format_str: str = "%H:%M") -> str:
    """Format UTC timestamp to location's local clock time."""
    local_dt = get_local_datetime(unix_timestamp, timezone_offset_seconds)
    return local_dt.strftime(format_str)


def format_date_local(unix_timestamp: int, timezone_offset_seconds: int = 0, format_str: str = "%a, %b %d") -> str:
    """Format UTC timestamp to location's local calendar date."""
    local_dt = get_local_datetime(unix_timestamp, timezone_offset_seconds)
    return local_dt.strftime(format_str)


def extract_hourly_forecast(
    forecast_list: List[Dict[str, Any]],
    timezone_offset_seconds: int = 0,
    max_intervals: int = 8,
) -> List[Dict[str, Any]]:
    """Extract and normalize upcoming forecast intervals (3-hour intervals).

    Free OpenWeatherMap 5-day / 3-hour forecast returns intervals.
    We extract the next intervals (up to max_intervals, e.g. 6 to 8 intervals = next 18-24 hours).
    """
    hourly_data: List[Dict[str, Any]] = []

    for item in forecast_list[:max_intervals]:
        dt = item.get("dt", 0)
        main = item.get("main", {})
        weather_items = item.get("weather", [])
        weather = weather_items[0] if weather_items else {}

        temp_c = float(main.get("temp", 0.0))
        feels_c = float(main.get("feels_like", temp_c))
        pop = float(item.get("pop", 0.0))  # Probability of precipitation (0.0 - 1.0)

        local_dt = get_local_datetime(dt, timezone_offset_seconds)
        time_display = local_dt.strftime("%H:%M")
        day_display = local_dt.strftime("%a")

        hourly_data.append({
            "timestamp": dt,
            "local_datetime": local_dt,
            "time_display": time_display,
            "day_display": day_display,
            "temp_c": temp_c,
            "feels_c": feels_c,
            "condition": weather.get("main", "Clear"),
            "description": weather.get("description", "clear sky").title(),
            "icon": weather.get("icon", "01d"),
            "pop_percent": int(round(pop * 100)),
            "humidity": main.get("humidity", 0),
        })

    return hourly_data


def group_five_day_forecast(
    forecast_list: List[Dict[str, Any]],
    timezone_offset_seconds: int = 0,
) -> List[Dict[str, Any]]:
    """Group 3-hour forecast intervals by local calendar day and derive daily summaries.

    Uses real intervals returned by OpenWeatherMap API:
    - Min and max temperatures calculated across all intervals in that local day.
    - Dominant condition and icon selected from midday intervals or most frequent.
    - Precipitation probability calculated as maximum pop in that day.
    """
    days_map: Dict[str, List[Dict[str, Any]]] = {}

    for item in forecast_list:
        dt = item.get("dt", 0)
        local_dt = get_local_datetime(dt, timezone_offset_seconds)
        date_key = local_dt.strftime("%Y-%m-%d")

        if date_key not in days_map:
            days_map[date_key] = []
        days_map[date_key].append(item)

    daily_summaries: List[Dict[str, Any]] = []

    # Sort days chronologically
    sorted_date_keys = sorted(days_map.keys())

    # We take up to 5 days
    for date_key in sorted_date_keys[:5]:
        intervals = days_map[date_key]
        if not intervals:
            continue

        temps: List[float] = []
        icons: List[str] = []
        conditions: List[str] = []
        descriptions: List[str] = []
        pops: List[float] = []
        humidities: List[int] = []

        # Find midday interval (around 12:00 - 15:00) if available for representative icon
        midday_weather: Optional[Dict[str, Any]] = None

        for it in intervals:
            dt = it.get("dt", 0)
            local_dt = get_local_datetime(dt, timezone_offset_seconds)
            main = it.get("main", {})
            w_list = it.get("weather", [])
            w = w_list[0] if w_list else {}

            temp = float(main.get("temp", 0.0))
            temps.append(temp)
            if "temp_min" in main:
                temps.append(float(main["temp_min"]))
            if "temp_max" in main:
                temps.append(float(main["temp_max"]))

            if "icon" in w:
                icons.append(w["icon"])
            if "main" in w:
                conditions.append(w["main"])
            if "description" in w:
                descriptions.append(w["description"])

            pops.append(float(it.get("pop", 0.0)))
            if "humidity" in main:
                humidities.append(int(main["humidity"]))

            # Midday preference (11am - 3pm)
            if 11 <= local_dt.hour <= 15 and midday_weather is None:
                midday_weather = w

        # Representative weather
        if midday_weather and "icon" in midday_weather:
            rep_icon = midday_weather["icon"]
            rep_condition = midday_weather.get("main", "Clear")
            rep_description = midday_weather.get("description", "clear sky").title()
        else:
            rep_icon = Counter(icons).most_common(1)[0][0] if icons else "01d"
            rep_condition = Counter(conditions).most_common(1)[0][0] if conditions else "Clear"
            rep_description = Counter(descriptions).most_common(1)[0][0].title() if descriptions else "Clear"

        # Representative sample date
        first_dt = intervals[0].get("dt", 0)
        local_sample_dt = get_local_datetime(first_dt, timezone_offset_seconds)

        daily_summaries.append({
            "date_key": date_key,
            "day_name": local_sample_dt.strftime("%A"),
            "short_day": local_sample_dt.strftime("%a"),
            "formatted_date": local_sample_dt.strftime("%b %d"),
            "temp_min_c": round(min(temps), 1) if temps else 0.0,
            "temp_max_c": round(max(temps), 1) if temps else 0.0,
            "condition": rep_condition,
            "description": rep_description,
            "icon": rep_icon,
            "max_pop_percent": int(round(max(pops) * 100)) if pops else 0,
            "avg_humidity": int(round(sum(humidities) / len(humidities))) if humidities else 0,
        })

    return daily_summaries


def generate_weather_insights(current_weather: Dict[str, Any], forecast_items: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """Generate meaningful, factual weather insights based on real API metrics."""
    insights: List[str] = []

    temp_c = current_weather.get("temp_c", 0.0)
    feels_c = current_weather.get("feels_c", temp_c)
    humidity = current_weather.get("humidity", 50)
    wind_mps = current_weather.get("wind_speed_mps", 0.0)
    condition = current_weather.get("condition", "").lower()
    description = current_weather.get("description", "").lower()

    # 1. Rain / Precipitation warning
    rain_terms = ("rain", "drizzle", "shower", "thunderstorm", "snow", "sleet")
    is_raining_now = any(term in condition or term in description for term in rain_terms)

    rain_in_forecast = False
    if forecast_items:
        for item in forecast_items[:4]:  # Next ~12 hours
            pop = item.get("pop_percent", 0)
            if pop >= 40:
                rain_in_forecast = True
                break

    if is_raining_now:
        insights.append("Precipitation is actively occurring. Remember to carry an umbrella and wear water-resistant footwear.")
    elif rain_in_forecast:
        insights.append("High probability of precipitation within the next 12 hours. Keep an umbrella handy.")

    # 2. Wind insight
    if wind_mps >= 10.8:  # Beaufort 6+ Strong breeze
        insights.append(f"Strong winds detected ({wind_mps * 3.6:.0f} km/h). Expect gusty outdoor conditions.")
    elif wind_mps >= 5.5:  # Moderate breeze
        insights.append(f"Moderate breeze present ({wind_mps * 3.6:.0f} km/h).")

    # 3. Feels-like divergence
    diff = round(feels_c - temp_c, 1)
    if diff >= 3.0:
        insights.append(f"Humidity makes it feel {abs(diff):.0f}° warmer than the actual temperature ({feels_c:.0f}°).")
    elif diff <= -3.0:
        insights.append(f"Wind chill makes it feel {abs(diff):.0f}° colder than the actual temperature ({feels_c:.0f}°).")

    # 4. Temperature extreme warnings
    if temp_c <= 0:
        insights.append("Freezing temperatures. Ensure protective winter wear and beware of icy patches.")
    elif temp_c >= 33:
        insights.append("High heat index. Stay well-hydrated and limit prolonged direct sun exposure.")

    # 5. Humidity extremes
    if humidity >= 85 and not is_raining_now:
        insights.append("High atmospheric humidity. Air will feel heavy and humid.")
    elif humidity <= 25:
        insights.append("Very dry air detected. Consider staying hydrated.")

    # Fallback if no specific warnings
    if not insights:
        if "clear" in condition or "clear" in description:
            insights.append("Clear skies and comfortable ambient conditions. Ideal weather for outdoor activities.")
        elif "cloud" in condition:
            insights.append("Partly cloudy skies with moderate ambient conditions.")
        else:
            insights.append("Current conditions are steady with no significant weather warnings.")

    return insights
