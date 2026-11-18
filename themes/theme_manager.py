"""Theme Manager providing dynamic styling and theme switching for Tkinter."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any, Callable, Dict, List

from themes.dark import DARK_THEME
from themes.light import LIGHT_THEME


class ThemeManager:
    """Manages active theme state and notifies listeners on theme change."""

    def __init__(self, initial_theme: str = "light") -> None:
        self._current_theme_name = initial_theme if initial_theme in ("light", "dark") else "light"
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    @property
    def current_theme_name(self) -> str:
        return self._current_theme_name

    @property
    def theme(self) -> Dict[str, Any]:
        return LIGHT_THEME if self._current_theme_name == "light" else DARK_THEME

    def toggle_theme(self) -> str:
        new_theme = "dark" if self._current_theme_name == "light" else "light"
        self.set_theme(new_theme)
        return new_theme

    def set_theme(self, theme_name: str) -> None:
        if theme_name not in ("light", "dark"):
            return
        if self._current_theme_name != theme_name:
            self._current_theme_name = theme_name
            self.notify_listeners()

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback when theme changes."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify_listeners(self) -> None:
        t = self.theme
        for listener in list(self._listeners):
            try:
                listener(t)
            except Exception:
                pass

    def apply_ttk_styles(self, root: tk.Misc) -> None:
        """Configure ttk styles to harmonize with current theme colors."""
        t = self.theme
        style = ttk.Style(root)

        # Use 'clam' or 'alt' for customizable widgets
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Base Frame styling
        style.configure("TFrame", background=t["bg"])
        style.configure("Surface.TFrame", background=t["surface"])
        style.configure("SecondarySurface.TFrame", background=t["surface_secondary"])

        # Base Label styling
        style.configure("TLabel", background=t["bg"], foreground=t["text_primary"])
        style.configure("Secondary.TLabel", background=t["bg"], foreground=t["text_secondary"])
        style.configure("Surface.TLabel", background=t["surface"], foreground=t["text_primary"])
        style.configure("SurfaceSecondary.TLabel", background=t["surface"], foreground=t["text_secondary"])

        # Entry styling
        style.configure(
            "TEntry",
            fieldbackground=t["input_bg"],
            foreground=t["input_fg"],
            bordercolor=t["input_border"],
            lightcolor=t["input_border"],
            darkcolor=t["input_border"],
            padding=6,
        )

        # Combobox styling
        style.configure(
            "TCombobox",
            fieldbackground=t["input_bg"],
            background=t["surface_secondary"],
            foreground=t["input_fg"],
            bordercolor=t["border"],
            arrowcolor=t["text_primary"],
            padding=4,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", t["input_bg"])],
            selectbackground=[("readonly", t["surface_secondary"])],
            selectforeground=[("readonly", t["text_primary"])],
        )

        # Scrollbar styling
        style.configure(
            "TScrollbar",
            background=t["surface_secondary"],
            troughcolor=t["bg"],
            bordercolor=t["border"],
            arrowcolor=t["text_secondary"],
        )


_global_theme_manager: ThemeManager | None = None


def get_theme_manager(initial_theme: str = "light") -> ThemeManager:
    global _global_theme_manager
    if _global_theme_manager is None:
        _global_theme_manager = ThemeManager(initial_theme=initial_theme)
    return _global_theme_manager


def get_theme(theme_name: str = "light") -> Dict[str, Any]:
    return LIGHT_THEME if theme_name == "light" else DARK_THEME
