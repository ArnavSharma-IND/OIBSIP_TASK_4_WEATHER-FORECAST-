"""Hourly Forecast component displaying upcoming 3-hour intervals in an open, floating horizontal strip."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List, Optional

from services.cache_service import cache_service
from utils.weather_helpers import format_temperature


class HourlyForecastView(tk.Frame):
    """Floating horizontal hourly forecast strip without repetitive boxed cards."""

    def __init__(self, parent: tk.Misc, theme: Dict[str, Any], **kwargs: Any) -> None:
        super().__init__(parent, bg=theme["bg"], **kwargs)
        self.theme = theme
        self.hourly_items: List[Dict[str, Any]] = []
        self.unit: str = "celsius"
        self._icon_refs: List[Any] = []

        self._build_ui()
        self.apply_theme(theme)

    def _build_ui(self) -> None:
        self.container = tk.Frame(self, bg=self.theme["bg"])
        self.container.pack(fill="x", expand=True, padx=24, pady=(8, 16))

        # Section Heading
        self.header_frame = tk.Frame(self.container, bg=self.theme["bg"])
        self.header_frame.pack(fill="x", anchor="w", pady=(0, 10))

        self.lbl_title = tk.Label(
            self.header_frame,
            text="HOURLY FORECAST",
            font=self.theme["font_section"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
            anchor="w",
        )
        self.lbl_title.pack(side="left")

        self.lbl_subtitle = tk.Label(
            self.header_frame,
            text="(3-hour API intervals, location local time)",
            font=self.theme["font_caption"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
            padx=8,
        )
        self.lbl_subtitle.pack(side="left")

        # Horizontal strip container
        self.strip_frame = tk.Frame(self.container, bg=self.theme["bg"])
        self.strip_frame.pack(fill="x", expand=True)

        # Empty state label
        self.lbl_empty = tk.Label(
            self.strip_frame,
            text="No forecast data loaded",
            font=self.theme["font_body"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
            pady=16,
        )
        self.lbl_empty.pack()

        # Thin bottom divider
        self.separator = tk.Frame(self.container, height=1, bg=self.theme["border_subtle"])
        self.separator.pack(fill="x", pady=(14, 0))

    def update_data(self, hourly_items: List[Dict[str, Any]], unit: str = "celsius") -> None:
        """Update hourly forecast data and re-render."""
        self.hourly_items = hourly_items
        self.unit = unit
        self.render()

    def set_unit(self, unit: str) -> None:
        """Update temperature unit dynamically."""
        if self.unit != unit:
            self.unit = unit
            if self.hourly_items:
                self.render()

    def render(self) -> None:
        """Render hourly items in an open horizontal layout."""
        # Clear previous children in strip frame
        for child in self.strip_frame.winfo_children():
            child.destroy()
        self._icon_refs.clear()

        if not self.hourly_items:
            self.lbl_empty = tk.Label(
                self.strip_frame,
                text="No forecast data loaded",
                font=self.theme["font_body"],
                bg=self.theme["bg"],
                fg=self.theme["text_secondary"],
                pady=16,
            )
            self.lbl_empty.pack()
            return

        # Display up to 6 to 8 intervals
        display_items = self.hourly_items[:6]
        count = len(display_items)

        for idx, item in enumerate(display_items):
            # Column container
            col = tk.Frame(self.strip_frame, bg=self.theme["bg"])
            col.pack(side="left", expand=True, fill="both", padx=(0, 6))

            # Time label (e.g. 15:00)
            time_lbl = tk.Label(
                col,
                text=item.get("time_display", "--:--"),
                font=self.theme["font_caption_bold"],
                bg=self.theme["bg"],
                fg=self.theme["text_secondary"],
            )
            time_lbl.pack(pady=(0, 4))

            # Weather Icon
            icon_lbl = tk.Label(col, bg=self.theme["bg"])
            icon_lbl.pack(pady=2)
            photo = cache_service.get_icon(item.get("icon", "01d"), size=(36, 36))
            if photo:
                icon_lbl.config(image=photo)
                self._icon_refs.append(photo)

            # Temperature
            temp_c = item.get("temp_c", 0.0)
            temp_str = format_temperature(temp_c, self.unit)
            temp_lbl = tk.Label(
                col,
                text=temp_str,
                font=self.theme["font_body_bold"],
                bg=self.theme["bg"],
                fg=self.theme["text_primary"],
            )
            temp_lbl.pack(pady=(2, 2))

            # Condition short name
            cond_lbl = tk.Label(
                col,
                text=item.get("condition", ""),
                font=self.theme["font_caption"],
                bg=self.theme["bg"],
                fg=self.theme["text_secondary"],
            )
            cond_lbl.pack(pady=(0, 2))

            # Precipitation probability badge (if > 0%)
            pop = item.get("pop_percent", 0)
            pop_text = f"☂ {pop}%" if pop > 0 else "—"
            pop_fg = self.theme["accent"] if pop >= 30 else self.theme["text_secondary"]
            pop_lbl = tk.Label(
                col,
                text=pop_text,
                font=self.theme["font_caption"],
                bg=self.theme["bg"],
                fg=pop_fg,
            )
            pop_lbl.pack()

            # Subtle vertical separator between hourly columns (except last)
            if idx < count - 1:
                divider = tk.Frame(self.strip_frame, width=1, bg=self.theme["border_subtle"])
                divider.pack(side="left", fill="y", padx=4, pady=6)

    def apply_theme(self, theme: Dict[str, Any]) -> None:
        """Apply theme styling to component."""
        self.theme = theme
        bg = theme["bg"]
        text_s = theme["text_secondary"]
        border_subtle = theme["border_subtle"]

        self.config(bg=bg)
        self.container.config(bg=bg)
        self.header_frame.config(bg=bg)
        self.strip_frame.config(bg=bg)
        self.separator.config(bg=border_subtle)

        self.lbl_title.config(bg=bg, fg=text_s, font=theme["font_section"])
        self.lbl_subtitle.config(bg=bg, fg=text_s, font=theme["font_caption"])

        if self.hourly_items:
            self.render()
        elif hasattr(self, "lbl_empty") and self.lbl_empty.winfo_exists():
            self.lbl_empty.config(bg=bg, fg=text_s, font=theme["font_body"])
