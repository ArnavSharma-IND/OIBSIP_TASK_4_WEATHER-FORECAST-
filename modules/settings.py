"""Settings modal dialog allowing configuration of API key, theme, units, and defaults."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from config import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    load_settings,
    save_settings,
)
from utils.validators import validate_api_key


class SettingsDialog(tk.Toplevel):
    """Configuration dialog for API keys and user preferences."""

    def __init__(
        self,
        parent: tk.Misc,
        theme: Dict[str, Any],
        on_save_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.on_save_callback = on_save_callback
        self.settings = load_settings()

        self.title("Application Settings")
        self.geometry("520x560")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(bg=self.theme["bg"])
        self._build_ui()

    def _build_ui(self) -> None:
        bg = self.theme["bg"]
        surface = self.theme["surface"]
        text_p = self.theme["text_primary"]
        text_s = self.theme["text_secondary"]
        accent = self.theme["accent"]

        container = tk.Frame(self, bg=bg, padx=24, pady=20)
        container.pack(fill="both", expand=True)

        # Dialog Title
        lbl_head = tk.Label(
            container,
            text="Preferences & Configuration",
            font=self.theme["font_title"],
            bg=bg,
            fg=text_p,
            anchor="w",
        )
        lbl_head.pack(fill="x", pady=(0, 16))

        # 1. API Configuration Section
        lbl_api_sec = tk.Label(
            container,
            text="OPENWEATHERMAP API CONFIGURATION",
            font=self.theme["font_section"],
            bg=bg,
            fg=text_s,
            anchor="w",
        )
        lbl_api_sec.pack(fill="x", pady=(8, 4))

        lbl_api_hint = tk.Label(
            container,
            text="A free key from openweathermap.org/api is required to query live weather.",
            font=self.theme["font_caption"],
            bg=bg,
            fg=text_s,
            anchor="w",
        )
        lbl_api_hint.pack(fill="x", pady=(0, 6))

        self.api_key_var = tk.StringVar(value=self.settings.get("api_key", ""))
        self.entry_api = tk.Entry(
            container,
            textvariable=self.api_key_var,
            font=self.theme["font_body"],
            bg=self.theme["input_bg"],
            fg=self.theme["input_fg"],
            bd=1,
            relief="solid",
            show="*",
        )
        self.entry_api.pack(fill="x", ipady=4, pady=(0, 4))

        self.show_key_var = tk.BooleanVar(value=False)
        chk_show = tk.Checkbutton(
            container,
            text="Reveal API Key",
            variable=self.show_key_var,
            command=self._toggle_show_key,
            bg=bg,
            fg=text_s,
            activebackground=bg,
            activeforeground=text_p,
            selectcolor=surface,
            font=self.theme["font_caption"],
        )
        chk_show.pack(anchor="w", pady=(0, 2))

        lbl_activation_note = tk.Label(
            container,
            text="* New OpenWeatherMap keys take 10 to 60 minutes to activate on their servers, and require confirming your registered email.",
            font=self.theme["font_caption"],
            bg=bg,
            fg=self.theme["accent"],
            anchor="w",
            wraplength=460,
            justify="left",
        )
        lbl_activation_note.pack(fill="x", pady=(0, 12))

        # 2. Units & Themes
        lbl_pref_sec = tk.Label(
            container,
            text="DISPLAY PREFERENCES",
            font=self.theme["font_section"],
            bg=bg,
            fg=text_s,
            anchor="w",
        )
        lbl_pref_sec.pack(fill="x", pady=(8, 6))

        # Unit Selection
        unit_frame = tk.Frame(container, bg=bg)
        unit_frame.pack(fill="x", pady=4)

        lbl_unit = tk.Label(unit_frame, text="Temperature Units:", font=self.theme["font_body"], bg=bg, fg=text_p)
        lbl_unit.pack(side="left")

        self.unit_var = tk.StringVar(value=self.settings.get("units", "celsius"))
        rb_c = tk.Radiobutton(
            unit_frame,
            text="Celsius (°C)",
            variable=self.unit_var,
            value="celsius",
            bg=bg,
            fg=text_p,
            selectcolor=surface,
            font=self.theme["font_body"],
        )
        rb_c.pack(side="left", padx=(16, 8))

        rb_f = tk.Radiobutton(
            unit_frame,
            text="Fahrenheit (°F)",
            variable=self.unit_var,
            value="fahrenheit",
            bg=bg,
            fg=text_p,
            selectcolor=surface,
            font=self.theme["font_body"],
        )
        rb_f.pack(side="left")

        # Theme Selection
        theme_frame = tk.Frame(container, bg=bg)
        theme_frame.pack(fill="x", pady=4)

        lbl_theme = tk.Label(theme_frame, text="Appearance Theme:", font=self.theme["font_body"], bg=bg, fg=text_p)
        lbl_theme.pack(side="left")

        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        rb_light = tk.Radiobutton(
            theme_frame,
            text="Light (Warm Beige)",
            variable=self.theme_var,
            value="light",
            bg=bg,
            fg=text_p,
            selectcolor=surface,
            font=self.theme["font_body"],
        )
        rb_light.pack(side="left", padx=(16, 8))

        rb_dark = tk.Radiobutton(
            theme_frame,
            text="Dark (Black & Violet)",
            variable=self.theme_var,
            value="dark",
            bg=bg,
            fg=text_p,
            selectcolor=surface,
            font=self.theme["font_body"],
        )
        rb_dark.pack(side="left")

        # Default Location
        loc_frame = tk.Frame(container, bg=bg)
        loc_frame.pack(fill="x", pady=8)

        lbl_loc = tk.Label(loc_frame, text="Default Startup City:", font=self.theme["font_body"], bg=bg, fg=text_p)
        lbl_loc.pack(side="left")

        self.default_loc_var = tk.StringVar(value=self.settings.get("default_location", "London"))
        self.entry_loc = tk.Entry(
            loc_frame,
            textvariable=self.default_loc_var,
            font=self.theme["font_body"],
            bg=self.theme["input_bg"],
            fg=self.theme["input_fg"],
            bd=1,
            relief="solid",
            width=24,
        )
        self.entry_loc.pack(side="left", padx=(16, 0), ipady=3)

        # Geolocation notice
        lbl_geo_notice = tk.Label(
            container,
            text="Note on Automatic Location: IP Geolocation queries external lookup service (ipinfo.io) and provides an approximate location based on your network route.",
            font=self.theme["font_caption"],
            bg=bg,
            fg=text_s,
            wraplength=460,
            justify="left",
        )
        lbl_geo_notice.pack(fill="x", pady=(10, 16))

        # Buttons
        btn_frame = tk.Frame(container, bg=bg)
        btn_frame.pack(fill="x", side="bottom")

        btn_cancel = tk.Button(
            btn_frame,
            text="Cancel",
            command=self.destroy,
            font=self.theme["font_body"],
            bg=self.theme["surface_secondary"],
            fg=text_p,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = tk.Button(
            btn_frame,
            text="Save Preferences",
            command=self._save,
            font=self.theme["font_body_bold"],
            bg=accent,
            fg=self.theme["accent_text"],
            bd=0,
            padx=18,
            pady=6,
            cursor="hand2",
        )
        btn_save.pack(side="right")

    def _toggle_show_key(self) -> None:
        if self.show_key_var.get():
            self.entry_api.config(show="")
        else:
            self.entry_api.config(show="*")

    def _save(self) -> None:
        key = self.api_key_var.get().strip().strip("'\"").strip()
        unit = self.unit_var.get()
        theme = self.theme_var.get()
        default_loc = self.default_loc_var.get().strip() or "London"

        # Validate API key if provided
        if key:
            is_valid, msg = validate_api_key(key)
            if not is_valid:
                if not messagebox.askyesno("Confirm API Key", f"{msg}\nDo you still wish to save this key?"):
                    return

        updated = {
            "api_key": key,
            "units": unit,
            "theme": theme,
            "default_location": default_loc,
        }

        save_settings(updated)

        if self.on_save_callback:
            self.on_save_callback(updated)

        self.destroy()
