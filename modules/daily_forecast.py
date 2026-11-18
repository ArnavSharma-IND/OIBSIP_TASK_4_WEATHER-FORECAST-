"""Five-Day Forecast component featuring a clean vertical list with subtle dividers."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List, Optional

from services.cache_service import cache_service
from utils.weather_helpers import format_temperature


class DailyForecastView(tk.Frame):
    """Clean vertical list displaying 5-day weather forecast."""

    def __init__(self, parent: tk.Misc, theme: Dict[str, Any], **kwargs: Any) -> None:
        super().__init__(parent, bg=theme["bg"], **kwargs)
        self.theme = theme
        self.daily_items: List[Dict[str, Any]] = []
        self.unit: str = "celsius"
        self._icon_refs: List[Any] = []

        self._build_ui()
        self.apply_theme(theme)

    def _build_ui(self) -> None:
        self.container = tk.Frame(self, bg=self.theme["bg"])
        self.container.pack(fill="x", expand=True, padx=24, pady=(8, 16))

        # Section Title
        self.header_frame = tk.Frame(self.container, bg=self.theme["bg"])
        self.header_frame.pack(fill="x", anchor="w", pady=(0, 10))

        self.lbl_title = tk.Label(
            self.header_frame,
            text="5-DAY FORECAST",
            font=self.theme["font_section"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
            anchor="w",
        )
        self.lbl_title.pack(side="left")

        # Vertical rows container
        self.list_frame = tk.Frame(self.container, bg=self.theme["bg"])
        self.list_frame.pack(fill="x", expand=True)

        self.lbl_empty = tk.Label(
            self.list_frame,
            text="No 5-day forecast data loaded",
            font=self.theme["font_body"],
            bg=self.theme["bg"],
            fg=self.theme["text_secondary"],
            pady=16,
        )
        self.lbl_empty.pack()

    def update_data(self, daily_items: List[Dict[str, Any]], unit: str = "celsius") -> None:
        """Update daily forecast items and re-render."""
        self.daily_items = daily_items
        self.unit = unit
        self.render()

    def set_unit(self, unit: str) -> None:
        """Update temperature unit dynamically."""
        if self.unit != unit:
            self.unit = unit
            if self.daily_items:
                self.render()

    def render(self) -> None:
        """Render daily forecast rows."""
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._icon_refs.clear()

        if not self.daily_items:
            self.lbl_empty = tk.Label(
                self.list_frame,
                text="No 5-day forecast data loaded",
                font=self.theme["font_body"],
                bg=self.theme["bg"],
                fg=self.theme["text_secondary"],
                pady=16,
            )
            self.lbl_empty.pack()
            return

        total_days = len(self.daily_items)
        for idx, day in enumerate(self.daily_items):
            # Row container (open, floating)
            row = tk.Frame(self.list_frame, bg=self.theme["bg"])
            row.pack(fill="x", expand=True, pady=6)

            # 1. Day of week & date
            date_col = tk.Frame(row, bg=self.theme["bg"], width=130)
            date_col.pack(side="left", fill="y")
            date_col.pack_propagate(False)

            day_name = day.get("day_name", "Day")
            date_str = day.get("formatted_date", "")

            lbl_day = tk.Label(
                date_col,
                text=day_name,
                font=self.theme["font_body_bold"],
                bg=self.theme["bg"],
                fg=self.theme["text_primary"],
                anchor="w",
            )
            lbl_day.pack(anchor="w")

            lbl_date = tk.Label(
                date_col,
                text=date_str,
                font=self.theme["font_caption"],
                bg=self.theme["bg"],
                fg=self.theme["text_secondary"],
                anchor="w",
            )
            lbl_date.pack(anchor="w")

            # 2. Weather Icon
            icon_col = tk.Frame(row, bg=self.theme["bg"], width=50)
            icon_col.pack(side="left", fill="y", padx=8)
            icon_col.pack_propagate(False)

            lbl_icon = tk.Label(icon_col, bg=self.theme["bg"])
            lbl_icon.pack(anchor="center")
            photo = cache_service.get_icon(day.get("icon", "01d"), size=(32, 32))
            if photo:
                lbl_icon.config(image=photo)
                self._icon_refs.append(photo)

            # 3. Condition Description + Rain probability
            cond_col = tk.Frame(row, bg=self.theme["bg"])
            cond_col.pack(side="left", expand=True, fill="x", padx=8)

            lbl_cond = tk.Label(
                cond_col,
                text=day.get("description", day.get("condition", "")),
                font=self.theme["font_body"],
                bg=self.theme["bg"],
                fg=self.theme["text_primary"],
                anchor="w",
            )
            lbl_cond.pack(anchor="w")

            pop = day.get("max_pop_percent", 0)
            pop_text = f"Precipitation chance: {pop}%" if pop > 0 else "Low precipitation risk"
            pop_fg = self.theme["accent"] if pop >= 40 else self.theme["text_secondary"]
            lbl_pop = tk.Label(
                cond_col,
                text=pop_text,
                font=self.theme["font_caption"],
                bg=self.theme["bg"],
                fg=pop_fg,
                anchor="w",
            )
            lbl_pop.pack(anchor="w")

            # 4. Temperature Range (Low ... High)
            temp_col = tk.Frame(row, bg=self.theme["bg"], width=130)
            temp_col.pack(side="right", fill="y")
            temp_col.pack_propagate(False)

            min_disp = format_temperature(day.get("temp_min_c", 0.0), self.unit)
            max_disp = format_temperature(day.get("temp_max_c", 0.0), self.unit)

            lbl_temp_range = tk.Label(
                temp_col,
                text=f"{min_disp}  /  {max_disp}",
                font=self.theme["font_body_bold"],
                bg=self.theme["bg"],
                fg=self.theme["text_primary"],
                anchor="e",
            )
            lbl_temp_range.pack(anchor="e")

            lbl_range_hint = tk.Label(
                temp_col,
                text="Low / High",
                font=self.theme["font_caption"],
                bg=self.theme["bg"],
                fg=self.theme["text_secondary"],
                anchor="e",
            )
            lbl_range_hint.pack(anchor="e")

            # Thin horizontal divider between rows
            if idx < total_days - 1:
                divider = tk.Frame(self.list_frame, height=1, bg=self.theme["border_subtle"])
                divider.pack(fill="x", pady=4)

    def apply_theme(self, theme: Dict[str, Any]) -> None:
        """Apply theme styling."""
        self.theme = theme
        bg = theme["bg"]
        text_s = theme["text_secondary"]

        self.config(bg=bg)
        self.container.config(bg=bg)
        self.header_frame.config(bg=bg)
        self.list_frame.config(bg=bg)
        self.lbl_title.config(bg=bg, fg=text_s, font=theme["font_section"])

        if self.daily_items:
            self.render()
        elif hasattr(self, "lbl_empty") and self.lbl_empty.winfo_exists():
            self.lbl_empty.config(bg=bg, fg=text_s, font=theme["font_body"])
