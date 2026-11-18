"""Favourites manager module for persisting and switching favourite locations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List, Optional

from config import FAVOURITES_FILE
from utils.logger import app_logger

DEFAULT_FAVOURITES = ["London, GB", "New York, US", "Tokyo, JP", "Paris, FR"]


class FavouritesManager:
    """Handles loading, saving, and querying favourite locations."""

    def __init__(self, file_path: Path = FAVOURITES_FILE) -> None:
        self.file_path = file_path
        self._favourites: List[str] = []
        self.load()

    def load(self) -> List[str]:
        """Load favourites from JSON file or initialize with defaults."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._favourites = [str(x).strip() for x in data if str(x).strip()]
                        return self._favourites
            except Exception as e:
                app_logger.warning("Failed to load favourites: %s", e)

        self._favourites = list(DEFAULT_FAVOURITES)
        self.save()
        return self._favourites

    def save(self) -> bool:
        """Persist favourites to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._favourites, f, indent=2)
            return True
        except Exception as e:
            app_logger.error("Failed to save favourites: %s", e)
            return False

    def get_all(self) -> List[str]:
        """Return list of saved favourite locations."""
        return list(self._favourites)

    def add(self, location: str) -> bool:
        """Add location to favourites if not already present."""
        clean = location.strip()
        if not clean:
            return False
        # Case-insensitive comparison
        if not any(f.lower() == clean.lower() for f in self._favourites):
            self._favourites.append(clean)
            self.save()
            return True
        return False

    def remove(self, location: str) -> bool:
        """Remove location from favourites."""
        clean = location.strip().lower()
        original_len = len(self._favourites)
        self._favourites = [f for f in self._favourites if f.strip().lower() != clean]
        if len(self._favourites) != original_len:
            self.save()
            return True
        return False

    def is_favourite(self, location: str) -> bool:
        """Check if location is currently in favourites."""
        clean = location.strip().lower()
        # Check direct or prefix match (e.g. "London" matches "London, GB")
        for f in self._favourites:
            f_clean = f.strip().lower()
            if f_clean == clean or f_clean.startswith(clean + ","):
                return True
        return False


# Global favourites instance
favourites_manager = FavouritesManager()
