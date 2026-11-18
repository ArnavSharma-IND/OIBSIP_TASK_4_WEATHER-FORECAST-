"""GUI workflow and state management tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from modules.favourites import FavouritesManager
from themes.dark import DARK_THEME
from themes.light import LIGHT_THEME
from themes.theme_manager import ThemeManager


class TestThemeAndFavouritesState:
    """Test theme toggling and favourites persistence workflows."""

    def test_theme_manager_toggle(self):
        manager = ThemeManager(initial_theme="light")
        assert manager.current_theme_name == "light"
        assert manager.theme["bg"] == LIGHT_THEME["bg"]

        # Toggle to dark
        new_theme = manager.toggle_theme()
        assert new_theme == "dark"
        assert manager.current_theme_name == "dark"
        assert manager.theme["bg"] == DARK_THEME["bg"]

        # Toggle back to light
        new_theme = manager.toggle_theme()
        assert new_theme == "light"
        assert manager.current_theme_name == "light"

    def test_theme_manager_listeners(self):
        manager = ThemeManager(initial_theme="light")
        mock_listener = MagicMock()
        manager.subscribe(mock_listener)

        manager.set_theme("dark")
        mock_listener.assert_called_once()
        assert mock_listener.call_args[0][0]["name"] == "dark"

    def test_favourites_manager_add_remove(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            fav_path = Path(tmp_dir) / "test_favs.json"
            fav_mgr = FavouritesManager(file_path=fav_path)

            # Initial defaults loaded
            assert len(fav_mgr.get_all()) > 0

            # Add new favorite
            assert fav_mgr.add("Berlin, DE") is True
            assert fav_mgr.is_favourite("Berlin, DE") is True
            assert fav_mgr.is_favourite("Berlin") is True

            # Duplicate add returns False
            assert fav_mgr.add("Berlin, DE") is False

            # Remove favorite
            assert fav_mgr.remove("Berlin, DE") is True
            assert fav_mgr.is_favourite("Berlin, DE") is False

            # Reload from disk
            new_mgr = FavouritesManager(file_path=fav_path)
            assert "Berlin, DE" not in new_mgr.get_all()
