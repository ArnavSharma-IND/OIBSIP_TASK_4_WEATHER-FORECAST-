"""Current Weather component featuring a minimalist, open floating layout."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List, Optional

from services.cache_service import cache_service
from utils.weather_helpers import (
    celsius_to_fahrenheit,
    format_pressure,
    format_temperature,
    format_time_local,
    format_visibility,
    format_wind_speed,
    generate_weather_insights,
)


class CurrentWeatherView(tk.Frame):
    """Minimalist floating current weather view."""

    def __init__(self, parent: tk.Misc, theme: Dict[str, Any], **kwargs: Any) -> None:
        super().__init__(parent, bg=theme["bg"], **kwargs)
        self.theme = theme
        self.current_data: Optional[Dict[str, Any]] = None
        self.timezone_offset: int = 0
        self.location_name: str = ""
        self.country: str = ""
        self.unit: str = "celsius"
        self.forecast_items: Optional[List[Dict[str, Any]]] = None

        self._build_ui()
        self.apply_theme(theme)

    def _build_ui(self) -> None:
        # Container frame
        self.container = tk.Frame(self, bg=self.theme["bg"])
        self.container.pack(fill="x", expand=True, padx=24, pady=(12, 16))

        # Top Section: Location & Date header
        self.header_frame = tk.Frame(self.container, bg=self.theme["bg"])
        self.header_frame.pack(fill="x", anchor="w")

        self.lbl_location = tk.Label(
            self.header_frame,
            text="Search a city to begin",
            font=self.theme["font_title"],
            bg=self.theme["bg"],
            fg=self.theme["text_primary"],
            anchor="w",
        )
        self.lbl_location.pack(side="left")

        self.lbl_country_badge = tk.Label(
            self.header_frame,
            text="",
            font=self.theme["font_caption_bold"],
            bg=self.theme["surface_secondary"],
            fg=self.theme["accent"],
            padx=8,
            pady=2,
        )
        self.lbl_country_badge.pack(side="left", padx=(10, 0))

        self.lbl_local_time = tk.Label(
            self.header_frame,
            text="",
            font=self.theme["font_body"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
        )
        self.lbl_local_time.pack(side="right")

        # Center Section: Hero Temperature & Condition (Floating, open)
        self.hero_frame = tk.Frame(self.container, bg=self.theme["bg"])
        self.hero_frame.pack(fill="x", pady=(8, 12))

        # Left hero: Big Temperature
        self.temp_frame = tk.Frame(self.hero_frame, bg=self.theme["bg"])
        self.temp_frame.pack(side="left", anchor="w")

        self.lbl_temp = tk.Label(
            self.temp_frame,
            text="--°",
            font=self.theme["font_temp_hero"],
            bg=self.theme["bg"],
            fg=self.theme["text_primary"],
        )
        self.lbl_temp.pack(side="left", anchor="s")

        self.lbl_alt_temp = tk.Label(
            self.temp_frame,
            text="",
            font=self.theme["font_subtitle"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
            padx=10,
        )
        self.lbl_alt_temp.pack(side="left", anchor="s", pady=(0, 10))

        # Right hero: Weather Icon + Condition description + High/Low
        self.condition_frame = tk.Frame(self.hero_frame, bg=self.theme["bg"])
        self.condition_frame.pack(side="left", padx=(30, 0), anchor="center")

        self.lbl_icon = tk.Label(self.condition_frame, bg=self.theme["bg"])
        self.lbl_icon.pack(side="left", padx=(0, 10))

        self.condition_text_frame = tk.Frame(self.condition_frame, bg=self.theme["bg"])
        self.condition_text_frame.pack(side="left")

        self.lbl_condition = tk.Label(
            self.condition_text_frame,
            text="",
            font=self.theme["font_subtitle"],
            bg=self.theme["bg"],
            fg=self.theme["text_primary"],
            anchor="w",
        )
        self.lbl_condition.pack(anchor="w")

        self.lbl_high_low = tk.Label(
            self.condition_text_frame,
            text="",
            font=self.theme["font_body"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
            anchor="w",
        )
        self.lbl_high_low.pack(anchor="w")

        # Weather Insights Banner (Clean editorial text, not a box)
        self.insight_frame = tk.Frame(self.container, bg=self.theme["surface"], bd=1, relief="solid")
        self.insight_frame.pack(fill="x", pady=(4, 16))

        self.lbl_insight = tk.Label(
            self.insight_frame,
            text="",
            font=self.theme["font_body"],
            bg=self.theme["surface"],
            fg=self.theme["accent"],
            padx=12,
            pady=8,
            anchor="w",
            wraplength=760,
            justify="left",
        )
        self.lbl_insight.pack(fill="x")

        # Thin Separator
        self.separator = tk.Frame(self.container, height=1, bg=self.theme["border_subtle"])
        self.separator.pack(fill="x", pady=(0, 12))

        # Bottom Section: Floating Metric Strip (Open layout with dividers, no boxy cards)
        self.metrics_bar = tk.Frame(self.container, bg=self.theme["bg"])
        self.metrics_bar.pack(fill="x")

        self.metric_widgets: Dict[str, Dict[str, tk.Label]] = {}
        metrics_specs = [
            ("feels_like", "FEELS LIKE"),
            ("humidity", "HUMIDITY"),
            ("wind", "WIND SPEED"),
            ("pressure", "PRESSURE"),
            ("visibility", "VISIBILITY"),
            ("sun", "SUNRISE / SUNSET"),
        ]

        total = len(metrics_specs)
        for i, (key, title) in enumerate(metrics_specs):
            m_frame = tk.Frame(self.metrics_bar, bg=self.theme["bg"])
            m_frame.pack(side="left", expand=True, fill="x", padx=(0, 8))

            title_lbl = tk.Label(
                m_frame,
                text=title,
                font=self.theme["font_caption_bold"],
                bg=self.theme["bg"],
                fg=self.theme["text_secondary"],
                anchor="w",
            )
            title_lbl.pack(anchor="w")

            val_lbl = tk.Label(
                m_frame,
                text="--",
                font=self.theme["font_body_bold"],
                bg=self.theme["bg"],
                fg=self.theme["text_primary"],
                anchor="w",
            )
            val_lbl.pack(anchor="w", pady=(2, 0))

            self.metric_widgets[key] = {"title": title_lbl, "value": val_lbl, "frame": m_frame}

            # Add subtle vertical divider between metrics (except after last)
            if i < total - 1:
                divider = tk.Frame(self.metrics_bar, width=1, bg=self.theme["border_subtle"])
                divider.pack(side="left", fill="y", padx=8, pady=4)

    def update_data(
        self,
        current: Dict[str, Any],
        timezone_offset: int,
        location_name: str,
        country: str,
        unit: str = "celsius",
        forecast_items: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Update view with fresh weather data."""
        self.current_data = current
        self.timezone_offset = timezone_offset
        self.location_name = location_name
        self.country = country
        self.unit = unit
        self.forecast_items = forecast_items

        self.render()

    def set_unit(self, unit: str) -> None:
        """Switch unit without re-fetching API."""
        if self.unit != unit:
            self.unit = unit
            if self.current_data:
                self.render()

    def render(self) -> None:
        """Render data to widgets."""
        if not self.current_data:
            return

        c = self.current_data
        tz = self.timezone_offset

        # Location and country badge
        self.lbl_location.config(text=self.location_name)
        if self.country:
            self.lbl_country_badge.config(text=self.country)
            self.lbl_country_badge.pack(side="left", padx=(10, 0))
        else:
            self.lbl_country_badge.pack_forget()

        # Local time at the searched location
        calc_dt_str = format_time_local(c.get("calc_time", 0), tz, format_str="%A, %H:%M")
        self.lbl_local_time.config(text=f"Local time: {calc_dt_str}")

        # Temperature
        temp_c = c.get("temp_c", 0.0)
        temp_f = celsius_to_fahrenheit(temp_c)
        feels_c = c.get("feels_c", temp_c)

        if self.unit == "fahrenheit":
            self.lbl_temp.config(text=f"{int(round(temp_f))}°F")
            self.lbl_alt_temp.config(text=f"({int(round(temp_c))}°C)")
        else:
            self.lbl_temp.config(text=f"{int(round(temp_c))}°C")
            self.lbl_alt_temp.config(text=f"({int(round(temp_f))}°F)")

        # Condition & High/Low
        self.lbl_condition.config(text=c.get("description", "").title())

        min_c = c.get("temp_min_c", temp_c)
        max_c = c.get("temp_max_c", temp_c)
        min_disp = format_temperature(min_c, self.unit)
        max_disp = format_temperature(max_c, self.unit)
        self.lbl_high_low.config(text=f"H: {max_disp}   L: {min_disp}")

        # Icon
        icon_code = c.get("icon", "01d")
        photo = cache_service.get_icon(icon_code, size=(54, 54))
        if photo:
            self.lbl_icon.config(image=photo)
            self.lbl_icon.image = photo  # Keep reference

        # Metrics
        feels_disp = format_temperature(feels_c, self.unit)
        self.metric_widgets["feels_like"]["value"].config(text=feels_disp)

        self.metric_widgets["humidity"]["value"].config(text=f"{c.get('humidity', 0)}%")

        wind_disp = format_wind_speed(c.get("wind_speed_mps", 0.0), self.unit)
        self.metric_widgets["wind"]["value"].config(text=wind_disp)

        self.metric_widgets["pressure"]["value"].config(text=format_pressure(c.get("pressure")))

        self.metric_widgets["visibility"]["value"].config(text=format_visibility(c.get("visibility_m"), self.unit))

        sunrise_str = format_time_local(c.get("sunrise", 0), tz) if c.get("sunrise") else "--:--"
        sunset_str = format_time_local(c.get("sunset", 0), tz) if c.get("sunset") else "--:--"
        self.metric_widgets["sun"]["value"].config(text=f"↑ {sunrise_str}   ↓ {sunset_str}")

        # Insights
        insights = generate_weather_insights(c, self.forecast_items)
        if insights:
            self.lbl_insight.config(text=insights[0])
            self.insight_frame.pack(fill="x", pady=(4, 16))
        else:
            self.insight_frame.pack_forget()

    def apply_theme(self, theme: Dict[str, Any]) -> None:
        """Apply theme styling."""
        self.theme = theme
        bg = theme["bg"]
        surface = theme["surface"]
        sec_surface = theme["surface_secondary"]
        text_p = theme["text_primary"]
        text_s = theme["text_secondary"]
        accent = theme["accent"]
        border_subtle = theme["border_subtle"]

        self.config(bg=bg)
        self.container.config(bg=bg)
        self.header_frame.config(bg=bg)
        self.hero_frame.config(bg=bg)
        self.temp_frame.config(bg=bg)
        self.condition_frame.config(bg=bg)
        self.condition_text_frame.config(bg=bg)
        self.metrics_bar.config(bg=bg)
        self.separator.config(bg=border_subtle)

        self.lbl_location.config(bg=bg, fg=text_p, font=theme["font_title"])
        self.lbl_country_badge.config(bg=sec_surface, fg=accent, font=theme["font_caption_bold"])
        self.lbl_local_time.config(bg=bg, fg=text_s, font=theme["font_body"])

        self.lbl_temp.config(bg=bg, fg=text_p, font=theme["font_temp_hero"])
        self.lbl_alt_temp.config(bg=bg, fg=text_s, font=theme["font_subtitle"])
        self.lbl_icon.config(bg=bg)
        self.lbl_condition.config(bg=bg, fg=text_p, font=theme["font_subtitle"])
        self.lbl_high_low.config(bg=bg, fg=text_s, font=theme["font_body"])

        self.insight_frame.config(bg=surface, highlightbackground=theme["border"], highlightcolor=theme["border"])
        self.lbl_insight.config(bg=surface, fg=accent, font=theme["font_body"])

        for m in self.metric_widgets.values():
            m["frame"].config(bg=bg)
            m["title"].config(bg=bg, fg=text_s, font=theme["font_caption_bold"])
            m["value"].config(bg=bg, fg=text_p, font=theme["font_body_bold"])

        # Re-render content with updated theme colors
        if self.current_data:
            self.render()
