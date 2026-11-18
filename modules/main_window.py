"""Main Application Window orchestrating GUI components, background threading,
event handling, and theme state.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

from config import (
    APP_NAME,
    APP_VERSION,
    get_api_key,
    load_settings,
    save_settings,
)
from modules.current_weather import CurrentWeatherView
from modules.daily_forecast import DailyForecastView
from modules.favourites import favourites_manager
from modules.hourly_forecast import HourlyForecastView
from modules.settings import SettingsDialog
from services.location_service import LocationService
from services.weather_api import WeatherAPIService, WeatherDataResult
from themes.theme_manager import get_theme_manager
from utils.logger import app_logger


class MainWindow(tk.Tk):
    """Production desktop GUI for Weather & Forecast application."""

    def __init__(self) -> None:
        super().__init__()

        # Load settings
        self.settings = load_settings()
        self.active_unit = self.settings.get("units", "celsius")
        self.theme_manager = get_theme_manager(initial_theme=self.settings.get("theme", "light"))

        # Initialize API service
        self.api_service = WeatherAPIService(
            api_key=self.settings.get("api_key", ""),
            timeout=self.settings.get("timeout_seconds", 10),
        )

        # Runtime state
        self.current_query = self.settings.get("default_location", "London")
        self.last_weather_result: Optional[WeatherDataResult] = None
        self.last_refresh_time: float = 0.0
        self.is_fetching: bool = False

        # Window configuration
        self.title(f"{APP_NAME} — Minimalist Desktop Weather")
        self.geometry("980x820")
        self.minsize(780, 640)

        # Build GUI
        self._build_layout()

        # Apply initial theme
        self.theme_manager.subscribe(self._on_theme_changed)
        self._apply_current_theme()

        # Load initial location
        self.after(200, self._load_initial_weather)

    def _build_layout(self) -> None:
        """Construct application interface with floating open canvas layout."""
        theme = self.theme_manager.theme

        # Top Control Header Bar
        self.header_bar = tk.Frame(self, bg=theme["surface"], bd=1, relief="solid")
        self.header_bar.pack(fill="x", padx=16, pady=(12, 6))

        # 1. Search Controls Group
        self.search_group = tk.Frame(self.header_bar, bg=theme["surface"])
        self.search_group.pack(side="left", padx=10, pady=8)

        self.search_var = tk.StringVar(value=self.current_query)
        self.entry_search = tk.Entry(
            self.search_group,
            textvariable=self.search_var,
            font=theme["font_body"],
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            bd=1,
            relief="solid",
            width=26,
        )
        self.entry_search.pack(side="left", ipady=4, padx=(0, 6))
        self.entry_search.bind("<Return>", lambda e: self.search_weather())

        self.btn_search = tk.Button(
            self.search_group,
            text="Search",
            command=self.search_weather,
            font=theme["font_body_bold"],
            bg=theme["accent"],
            fg=theme["accent_text"],
            activebackground=theme["accent_hover"],
            activeforeground=theme["accent_text"],
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
        )
        self.btn_search.pack(side="left", padx=(0, 6))

        # Geolocation button
        self.btn_locate = tk.Button(
            self.search_group,
            text="📍 Auto",
            command=self.detect_location,
            font=theme["font_body"],
            bg=theme["surface_secondary"],
            fg=theme["text_primary"],
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
        )
        self.btn_locate.pack(side="left")

        # 2. Favourites Group
        self.fav_group = tk.Frame(self.header_bar, bg=theme["surface"])
        self.fav_group.pack(side="left", padx=10, pady=8)

        lbl_fav = tk.Label(
            self.fav_group,
            text="Saved:",
            font=theme["font_caption_bold"],
            bg=theme["surface"],
            fg=theme["text_secondary"],
        )
        lbl_fav.pack(side="left", padx=(0, 4))

        self.fav_var = tk.StringVar()
        self.combo_fav = ttk.Combobox(
            self.fav_group,
            textvariable=self.fav_var,
            values=favourites_manager.get_all(),
            state="readonly",
            width=16,
        )
        self.combo_fav.pack(side="left", padx=(0, 4))
        self.combo_fav.bind("<<ComboboxSelected>>", self._on_favourite_selected)

        # Star toggle button
        self.btn_star = tk.Button(
            self.fav_group,
            text="☆",
            command=self.toggle_favourite,
            font=("Segoe UI", 12),
            bg=theme["surface"],
            fg=theme["accent"],
            bd=0,
            cursor="hand2",
            padx=4,
        )
        self.btn_star.pack(side="left")

        # 3. Actions Group (Right-aligned)
        self.actions_group = tk.Frame(self.header_bar, bg=theme["surface"])
        self.actions_group.pack(side="right", padx=10, pady=8)

        # Unit Toggle (°C / °F)
        unit_text = "°C" if self.active_unit == "celsius" else "°F"
        self.btn_unit = tk.Button(
            self.actions_group,
            text=f"Units: {unit_text}",
            command=self.toggle_unit,
            font=theme["font_body_bold"],
            bg=theme["surface_secondary"],
            fg=theme["text_primary"],
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.btn_unit.pack(side="left", padx=(0, 6))

        # Theme Toggle
        theme_icon = "☼ Light" if self.theme_manager.current_theme_name == "light" else "☽ Dark"
        self.btn_theme = tk.Button(
            self.actions_group,
            text=theme_icon,
            command=self.toggle_theme,
            font=theme["font_body"],
            bg=theme["surface_secondary"],
            fg=theme["text_primary"],
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.btn_theme.pack(side="left", padx=(0, 6))

        # Refresh Button
        self.btn_refresh = tk.Button(
            self.actions_group,
            text="⟳ Refresh",
            command=lambda: self.search_weather(force_refresh=True),
            font=theme["font_body"],
            bg=theme["surface_secondary"],
            fg=theme["text_primary"],
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.btn_refresh.pack(side="left", padx=(0, 6))

        # Settings Button
        self.btn_settings = tk.Button(
            self.actions_group,
            text="⚙",
            command=self.open_settings,
            font=("Segoe UI", 11),
            bg=theme["surface_secondary"],
            fg=theme["text_primary"],
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
        )
        self.btn_settings.pack(side="left")

        # In-App Notification / Error Banner (Hidden by default)
        self.banner_frame = tk.Frame(self, bg=theme["error_bg"], bd=1, relief="solid")
        self.lbl_banner = tk.Label(
            self.banner_frame,
            text="",
            font=theme["font_body"],
            bg=theme["error_bg"],
            fg=theme["error_fg"],
            padx=14,
            pady=8,
            anchor="w",
            wraplength=800,
            justify="left",
        )
        self.lbl_banner.pack(side="left", fill="x", expand=True)

        self.btn_dismiss_banner = tk.Button(
            self.banner_frame,
            text="✕",
            command=self.hide_notification,
            font=theme["font_caption_bold"],
            bg=theme["error_bg"],
            fg=theme["error_fg"],
            bd=0,
            padx=10,
            cursor="hand2",
        )
        self.btn_dismiss_banner.pack(side="right")

        # Loading / Status Strip
        self.status_bar = tk.Frame(self, bg=theme["bg"])
        self.status_bar.pack(fill="x", padx=20, pady=(2, 0))

        self.lbl_status = tk.Label(
            self.status_bar,
            text="Ready",
            font=theme["font_caption"],
            bg=theme["bg"],
            fg=theme["text_secondary"],
            anchor="w",
        )
        self.lbl_status.pack(side="left")

        self.lbl_updated = tk.Label(
            self.status_bar,
            text="",
            font=theme["font_caption"],
            bg=theme["bg"],
            fg=theme["text_secondary"],
            anchor="e",
        )
        self.lbl_updated.pack(side="right")

        # Main Scrollable Content Canvas
        self.canvas_container = tk.Frame(self, bg=theme["bg"])
        self.canvas_container.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self.canvas = tk.Canvas(self.canvas_container, bg=theme["bg"], highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.canvas_container, orient="vertical", command=self.canvas.yview)
        self.content_frame = tk.Frame(self.canvas, bg=theme["bg"])

        self.content_window_id = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Configure responsive resizing of the content frame inside canvas
        self.content_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.content_window_id, width=e.width),
        )

        # Mouse wheel binding
        self.bind_all("<MouseWheel>", self._on_mousewheel)

        # Child Views
        self.current_weather_view = CurrentWeatherView(self.content_frame, theme=theme)
        self.current_weather_view.pack(fill="x", expand=True)

        self.hourly_forecast_view = HourlyForecastView(self.content_frame, theme=theme)
        self.hourly_forecast_view.pack(fill="x", expand=True)

        self.daily_forecast_view = DailyForecastView(self.content_frame, theme=theme)
        self.daily_forecast_view.pack(fill="x", expand=True)

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle smooth canvas mousewheel scroll."""
        if self.canvas.winfo_exists():
            # Windows scroll direction
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # -----------------------------------------------------------------
    # Weather Fetching & Background Threading
    # -----------------------------------------------------------------
    def _load_initial_weather(self) -> None:
        """Fetch default weather on startup."""
        loc = self.settings.get("default_location", "London")
        self.search_weather(location=loc)

    def search_weather(self, location: Optional[str] = None, force_refresh: bool = False) -> None:
        """Execute a weather search asynchronously in a background thread."""
        if self.is_fetching:
            return

        query = location if location is not None else self.search_var.get().strip()
        if not query:
            self.show_notification("Please enter a city name, 'City, Country', or postal code.", is_error=True)
            return

        # Debounce refresh action to avoid overwhelming API
        now = time.time()
        if force_refresh and (now - self.last_refresh_time < 3.0):
            self.show_notification("Please wait a few seconds before refreshing again.", is_error=False)
            return

        self.hide_notification()
        self.is_fetching = True
        self.current_query = query
        self.search_var.set(query)
        self._set_loading_state(True)

        # Background worker thread
        def worker() -> None:
            try:
                res = self.api_service.fetch_weather(query, force_refresh=force_refresh)
            except Exception as e:
                res = WeatherDataResult(
                    success=False,
                    error_message=f"Unexpected error: {str(e)}",
                    error_code="CLIENT_ERROR",
                )
            # Safe dispatch to Tkinter main UI thread
            try:
                if self.winfo_exists():
                    self.after(0, self._on_weather_fetched, res, force_refresh)
            except Exception:
                pass

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_weather_fetched(self, result: WeatherDataResult, forced: bool) -> None:
        """Handle returned weather data on the main UI thread."""
        self.is_fetching = False
        self._set_loading_state(False)
        self.last_weather_result = result

        if not result.success:
            self.lbl_status.config(text="Search failed")
            self.show_notification(result.error_message, is_error=True)
            return

        self.last_refresh_time = time.time()
        source_note = " (cached)" if result.from_cache else " (live API)"
        self.lbl_status.config(text=f"Loaded weather for {result.location_name}{source_note}")

        update_str = time.strftime("%H:%M:%S", time.localtime(result.last_updated))
        self.lbl_updated.config(text=f"Last updated: {update_str}")

        # Update child views
        if result.current:
            self.current_weather_view.update_data(
                current=result.current,
                timezone_offset=result.timezone_offset,
                location_name=result.location_name,
                country=result.country,
                unit=self.active_unit,
                forecast_items=result.hourly,
            )

        if result.hourly:
            self.hourly_forecast_view.update_data(result.hourly, unit=self.active_unit)

        if result.daily:
            self.daily_forecast_view.update_data(result.daily, unit=self.active_unit)

        # Update star button state
        self._update_star_button(result.location_name)

    def _set_loading_state(self, loading: bool) -> None:
        """Update UI state during network requests."""
        if loading:
            self.btn_search.config(state="disabled", text="Loading...")
            self.lbl_status.config(text=f"Fetching weather for '{self.current_query}' from OpenWeatherMap...")
        else:
            self.btn_search.config(state="normal", text="Search")

    # -----------------------------------------------------------------
    # Notification Banner
    # -----------------------------------------------------------------
    def show_notification(self, message: str, is_error: bool = True) -> None:
        """Display non-blocking notification banner inside the GUI."""
        theme = self.theme_manager.theme
        if is_error:
            bg_color = theme["error_bg"]
            fg_color = theme["error_fg"]
            border_col = theme["error_border"]
        else:
            bg_color = theme["surface_secondary"]
            fg_color = theme["text_primary"]
            border_col = theme["border"]

        self.banner_frame.config(bg=bg_color, highlightbackground=border_col, highlightcolor=border_col)
        self.lbl_banner.config(text=message, bg=bg_color, fg=fg_color)
        self.btn_dismiss_banner.config(bg=bg_color, fg=fg_color)

        # Pack banner right below header bar
        self.banner_frame.pack(fill="x", padx=16, pady=(0, 6), before=self.status_bar)

    def hide_notification(self) -> None:
        """Hide notification banner."""
        self.banner_frame.pack_forget()

    # -----------------------------------------------------------------
    # Unit Toggle (°C / °F)
    # -----------------------------------------------------------------
    def toggle_unit(self) -> None:
        """Toggle between Celsius and Fahrenheit dynamically without API re-query."""
        new_unit = "fahrenheit" if self.active_unit == "celsius" else "celsius"
        self.active_unit = new_unit

        # Update button label
        unit_text = "°C" if self.active_unit == "celsius" else "°F"
        self.btn_unit.config(text=f"Units: {unit_text}")

        # Update views
        self.current_weather_view.set_unit(new_unit)
        self.hourly_forecast_view.set_unit(new_unit)
        self.daily_forecast_view.set_unit(new_unit)

        # Save preference
        self.settings["units"] = new_unit
        save_settings({"units": new_unit})
        app_logger.info("Temperature unit toggled to: %s", new_unit)

    # -----------------------------------------------------------------
    # Theme Toggle (Light / Dark)
    # -----------------------------------------------------------------
    def toggle_theme(self) -> None:
        """Toggle between Light and Dark mode."""
        new_theme = self.theme_manager.toggle_theme()
        self.settings["theme"] = new_theme
        save_settings({"theme": new_theme})

    def _on_theme_changed(self, theme: Dict[str, Any]) -> None:
        """Listener triggered when theme changes."""
        self._apply_current_theme()

    def _apply_current_theme(self) -> None:
        """Apply theme colors across all widgets in the main window."""
        theme = self.theme_manager.theme
        self.theme_manager.apply_ttk_styles(self)

        bg = theme["bg"]
        surface = theme["surface"]
        sec_surface = theme["surface_secondary"]
        text_p = theme["text_primary"]
        text_s = theme["text_secondary"]
        accent = theme["accent"]
        border = theme["border"]

        self.configure(bg=bg)
        self.header_bar.configure(bg=surface, highlightbackground=border, highlightcolor=border)
        self.search_group.configure(bg=surface)
        self.fav_group.configure(bg=surface)
        self.actions_group.configure(bg=surface)
        self.status_bar.configure(bg=bg)
        self.canvas_container.configure(bg=bg)
        self.canvas.configure(bg=bg)
        self.content_frame.configure(bg=bg)

        # Entry & Buttons
        self.entry_search.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            highlightbackground=theme["input_border"],
            highlightcolor=accent,
            font=theme["font_body"],
        )
        self.btn_search.configure(
            bg=accent,
            fg=theme["accent_text"],
            activebackground=theme["accent_hover"],
            activeforeground=theme["accent_text"],
        )
        self.btn_locate.configure(bg=sec_surface, fg=text_p)
        self.btn_star.configure(bg=surface, fg=accent)
        self.btn_unit.configure(bg=sec_surface, fg=text_p)

        theme_text = "☼ Light" if self.theme_manager.current_theme_name == "light" else "☽ Dark"
        self.btn_theme.configure(text=theme_text, bg=sec_surface, fg=text_p)
        self.btn_refresh.configure(bg=sec_surface, fg=text_p)
        self.btn_settings.configure(bg=sec_surface, fg=text_p)

        self.lbl_status.configure(bg=bg, fg=text_s)
        self.lbl_updated.configure(bg=bg, fg=text_s)

        # Propagate to child views
        self.current_weather_view.apply_theme(theme)
        self.hourly_forecast_view.apply_theme(theme)
        self.daily_forecast_view.apply_theme(theme)

    # -----------------------------------------------------------------
    # Favourites Handling
    # -----------------------------------------------------------------
    def toggle_favourite(self) -> None:
        """Add or remove current location from favourites."""
        loc = self.last_weather_result.location_name if self.last_weather_result else self.current_query
        if not loc:
            return

        if favourites_manager.is_favourite(loc):
            favourites_manager.remove(loc)
            self.show_notification(f"Removed '{loc}' from saved locations.", is_error=False)
        else:
            favourites_manager.add(loc)
            self.show_notification(f"Added '{loc}' to saved locations.", is_error=False)

        self._refresh_favourites_dropdown()
        self._update_star_button(loc)

    def _update_star_button(self, location_name: str) -> None:
        """Update star icon based on favourite status."""
        if favourites_manager.is_favourite(location_name):
            self.btn_star.config(text="★")
        else:
            self.btn_star.config(text="☆")

    def _refresh_favourites_dropdown(self) -> None:
        """Refresh combobox values."""
        self.combo_fav.config(values=favourites_manager.get_all())

    def _on_favourite_selected(self, event: tk.Event) -> None:
        """Handle selection from favourite locations combobox."""
        selected = self.fav_var.get().strip()
        if selected:
            self.search_weather(location=selected)

    # -----------------------------------------------------------------
    # Geolocation Detection (Bonus Feature)
    # -----------------------------------------------------------------
    def detect_location(self) -> None:
        """Detect approximate location using IP Geolocation with explicit consent."""
        consent_msg = (
            "Would you like to detect your approximate location using IP Geolocation?\n\n"
            "Privacy notice:\n"
            "• This makes a request to ipinfo.io to find your approximate city.\n"
            "• IP geolocation is based on ISP routing and may not be exact.\n"
            "• No personal data is stored."
        )
        if not messagebox.askyesno("Detect Approximate Location", consent_msg, parent=self):
            return

        self.show_notification("Detecting location via IP...", is_error=False)

        def worker() -> None:
            ok, msg, data = LocationService.detect_approximate_location()

            def finish() -> None:
                if ok and data:
                    detected_city = data["query_string"]
                    self.show_notification(f"Detected: {detected_city}. Loading weather...", is_error=False)
                    self.search_weather(location=detected_city)
                else:
                    self.show_notification(msg, is_error=True)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    # -----------------------------------------------------------------
    # Settings Dialog
    # -----------------------------------------------------------------
    def open_settings(self) -> None:
        """Open settings dialog."""
        SettingsDialog(self, theme=self.theme_manager.theme, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self, new_settings: Dict[str, Any]) -> None:
        """Apply newly saved settings."""
        self.settings.update(new_settings)

        # Update API service key
        new_key = new_settings.get("api_key", "")
        self.api_service.set_api_key(new_key)

        # Update unit
        unit = new_settings.get("units", "celsius")
        if unit != self.active_unit:
            self.active_unit = unit
            unit_text = "°C" if self.active_unit == "celsius" else "°F"
            self.btn_unit.config(text=f"Units: {unit_text}")
            self.current_weather_view.set_unit(unit)
            self.hourly_forecast_view.set_unit(unit)
            self.daily_forecast_view.set_unit(unit)

        # Update theme
        theme_name = new_settings.get("theme", "light")
        if theme_name != self.theme_manager.current_theme_name:
            self.theme_manager.set_theme(theme_name)

        self.show_notification("Settings saved successfully.", is_error=False)
