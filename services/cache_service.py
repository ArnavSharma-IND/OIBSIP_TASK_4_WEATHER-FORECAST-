"""Cache service for API responses, icons, and persistent assets."""

from __future__ import annotations

import io
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageTk

from config import ICONS_CACHE_DIR, OWM_ICON_URL_TEMPLATE
from utils.logger import app_logger


class CacheService:
    """Manages memory and filesystem caching for weather responses and weather icons."""

    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl_seconds = ttl_seconds
        self._memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._photo_cache: Dict[str, ImageTk.PhotoImage] = {}
        ICONS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # Response Caching
    # ---------------------------------------------------------
    def get_weather(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve unexpired cached weather data if present."""
        normalized_key = cache_key.strip().lower()
        if normalized_key in self._memory_cache:
            timestamp, data = self._memory_cache[normalized_key]
            if time.time() - timestamp < self.ttl_seconds:
                app_logger.debug("Memory cache hit for %s", normalized_key)
                return data
            else:
                del self._memory_cache[normalized_key]
        return None

    def set_weather(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store weather data in memory cache."""
        normalized_key = cache_key.strip().lower()
        self._memory_cache[normalized_key] = (time.time(), data)

    def clear_weather_cache(self) -> None:
        """Clear memory cache for weather queries."""
        self._memory_cache.clear()

    def clear_icon_cache(self) -> None:
        """Clear memory cache for Tk PhotoImages."""
        self._photo_cache.clear()

    # ---------------------------------------------------------
    # Icon Caching & Processing (Pillow)
    # ---------------------------------------------------------
    def get_icon(self, icon_code: str, size: Tuple[int, int] = (48, 48)) -> Optional[ImageTk.PhotoImage]:
        """Retrieve weather icon as ImageTk.PhotoImage, loading from disk cache
        or downloading from OpenWeatherMap CDN. Falls back to clean drawn shape.
        """
        if not icon_code:
            icon_code = "01d"

        cache_id = f"{icon_code}_{size[0]}x{size[1]}"
        if cache_id in self._photo_cache:
            return self._photo_cache[cache_id]

        icon_file = ICONS_CACHE_DIR / f"{icon_code}.png"
        pil_image: Optional[Image.Image] = None

        # 1. Try reading from disk
        if icon_file.exists():
            try:
                pil_image = Image.open(icon_file).convert("RGBA")
            except Exception as e:
                app_logger.warning("Failed to open cached icon %s: %s", icon_file, e)

        # 2. Try downloading if not on disk
        if pil_image is None:
            url = OWM_ICON_URL_TEMPLATE.format(icon=icon_code)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 WeatherApp/1.0",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    pil_image = Image.open(io.BytesIO(response.content)).convert("RGBA")
                    # Save to local cache
                    pil_image.save(icon_file, format="PNG")
                    app_logger.debug("Downloaded and cached icon: %s", icon_code)
                else:
                    app_logger.warning("Icon download failed with status %d for %s", response.status_code, icon_code)
            except Exception as e:
                app_logger.debug("Could not download icon %s (offline or network): %s", icon_code, e)

        # 3. Fallback: Draw procedural weather placeholder icon
        if pil_image is None:
            pil_image = self._create_procedural_icon(icon_code, size)

        # Resize keeping smooth antialiasing
        resized = pil_image.resize(size, Image.Resampling.LANCZOS)
        try:
            photo = ImageTk.PhotoImage(resized)
            self._photo_cache[cache_id] = photo
            return photo
        except Exception as e:
            app_logger.error("Failed to create PhotoImage for %s: %s", icon_code, e)
            return None

    def _create_procedural_icon(self, icon_code: str, size: Tuple[int, int]) -> Image.Image:
        """Create a clean procedural weather icon placeholder when offline."""
        img = Image.new("RGBA", size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        w, h = size
        padding = max(2, w // 8)

        # Check icon condition by prefix
        code_prefix = icon_code[:2] if len(icon_code) >= 2 else "01"
        is_night = icon_code.endswith("n")

        if code_prefix == "01":  # Clear sky (Sun / Moon)
            if is_night:
                # Moon crescent
                draw.ellipse([padding, padding, w - padding, h - padding], fill=(180, 180, 210, 220))
                draw.ellipse([padding + w // 4, padding - h // 8, w, h - padding], fill=(0, 0, 0, 0))
            else:
                # Sun
                draw.ellipse([padding, padding, w - padding, h - padding], fill=(230, 140, 50, 230))
        elif code_prefix in ("02", "03", "04"):  # Clouds
            # Cloud shapes
            draw.ellipse([padding, h // 3, w - padding, h - padding], fill=(170, 175, 185, 220))
            draw.ellipse([w // 4, padding, w * 3 // 4, h * 2 // 3], fill=(190, 195, 205, 220))
        elif code_prefix in ("09", "10", "11"):  # Rain / Thunderstorm
            # Cloud + rain lines
            draw.ellipse([padding, padding, w - padding, h * 3 // 5], fill=(120, 135, 155, 220))
            for x in (w // 3, w // 2, w * 2 // 3):
                draw.line([(x, h * 3 // 5 + 2), (x - 2, h - padding)], fill=(80, 130, 200, 220), width=2)
        elif code_prefix == "13":  # Snow
            draw.ellipse([padding, padding, w - padding, h * 3 // 5], fill=(180, 195, 215, 220))
            for x, y in [(w // 3, h * 3 // 4), (w // 2, h * 4 // 5), (w * 2 // 3, h * 3 // 4)]:
                draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(220, 235, 255, 240))
        else:  # Mist / Atmosphere / Other
            for y in (h // 3, h // 2, h * 2 // 3):
                draw.line([(padding, y), (w - padding, y)], fill=(160, 160, 170, 200), width=2)

        return img


# Global cache instance
cache_service = CacheService(ttl_seconds=600)
