"""Screenshot capture utility using high-fidelity Windows client area rendering."""

import ctypes
import os
import time
from unittest.mock import patch

from PIL import Image

from config import save_settings
from modules.main_window import MainWindow
from services.cache_service import cache_service
from services.weather_api import WeatherDataResult

# Real OpenWeatherMap payload for London (Haze, 8.26 C, 95% humidity)
MOCK_CURRENT = {
    "temp_c": 8.26,
    "feels_c": 8.26,
    "temp_min_c": 7.53,
    "temp_max_c": 8.89,
    "humidity": 95,
    "pressure": 1026,
    "visibility_m": 2900,
    "wind_speed_mps": 0.0,
    "wind_deg": 0,
    "condition": "Haze",
    "description": "Haze",
    "icon": "50d",
    "sunrise": 1745728782,
    "sunset": 1745781377,
    "calc_time": 1745735677,
}

MOCK_HOURLY = [
    {"time_display": "09:00", "temp_c": 8.3, "condition": "Haze", "icon": "50d", "pop_percent": 10},
    {"time_display": "12:00", "temp_c": 8.9, "condition": "Clouds", "icon": "03d", "pop_percent": 15},
    {"time_display": "15:00", "temp_c": 8.5, "condition": "Clouds", "icon": "04d", "pop_percent": 20},
    {"time_display": "18:00", "temp_c": 8.0, "condition": "Rain", "icon": "10d", "pop_percent": 45},
    {"time_display": "21:00", "temp_c": 7.6, "condition": "Rain", "icon": "10n", "pop_percent": 60},
    {"time_display": "00:00", "temp_c": 7.2, "condition": "Overcast", "icon": "04n", "pop_percent": 25},
]

MOCK_DAILY = [
    {"day_name": "Tuesday", "formatted_date": "Apr 27", "temp_min_c": 7.5, "temp_max_c": 8.9, "condition": "Haze", "description": "Atmospheric Haze", "icon": "50d", "max_pop_percent": 20},
    {"day_name": "Wednesday", "formatted_date": "Apr 28", "temp_min_c": 6.8, "temp_max_c": 10.2, "condition": "Rain", "description": "Light Rain Showers", "icon": "10d", "max_pop_percent": 70},
    {"day_name": "Thursday", "formatted_date": "Apr 29", "temp_min_c": 5.5, "temp_max_c": 11.0, "condition": "Partly Cloudy", "description": "Scattered Clouds", "icon": "02d", "max_pop_percent": 10},
    {"day_name": "Friday", "formatted_date": "Apr 30", "temp_min_c": 7.0, "temp_max_c": 12.4, "condition": "Clouds", "description": "Broken Clouds", "icon": "03d", "max_pop_percent": 15},
    {"day_name": "Saturday", "formatted_date": "May 01", "temp_min_c": 8.1, "temp_max_c": 13.5, "condition": "Sunny", "description": "Clear Sky", "icon": "01d", "max_pop_percent": 5},
]


def capture_window_hwnd(hwnd: int) -> Image.Image:
    """Capture exact window content directly from Windows DWM using PrintWindow."""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hwnd_dc = user32.GetDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    gdi32.SelectObject(mem_dc, bitmap)

    # 2 = PW_RENDERFULLCONTENT
    user32.PrintWindow(hwnd, mem_dc, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32),
            ("biWidth", ctypes.c_int32),
            ("biHeight", ctypes.c_int32),
            ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16),
            ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32),
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h  # top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem_dc, bitmap, 0, h, buf, ctypes.byref(bmi), 0)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)

    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    return img.convert("RGB")


def capture_mode(theme_name: str, filename: str) -> None:
    cache_service.clear_icon_cache()
    save_settings({"theme": theme_name})
    from themes.theme_manager import get_theme_manager
    get_theme_manager().set_theme(theme_name)

    sample_result = WeatherDataResult(
        success=True,
        location_name="London",
        country="GB",
        timezone_offset=3600,
        current=MOCK_CURRENT,
        hourly=MOCK_HOURLY,
        daily=MOCK_DAILY,
        last_updated=time.time(),
        from_cache=False,
    )

    with patch.object(MainWindow, "_load_initial_weather"):
        app = MainWindow()
        app.theme_manager.set_theme(theme_name)
        app.geometry("980x820+40+40")
        app.deiconify()
        app.lift()
        app.attributes("-topmost", True)
        app.update_idletasks()
        app._on_weather_fetched(sample_result, forced=False)
        app.update_idletasks()
        app.update()
        time.sleep(0.6)

        hwnd = app.winfo_id()
        img = capture_window_hwnd(hwnd)
        img.save(filename, format="PNG")
        print(f"Captured {filename}: {img.size}")
        app.quit()
        app.destroy()


def main() -> None:
    os.makedirs("assets/screenshots", exist_ok=True)
    capture_mode("light", "assets/screenshots/light_mode.png")
    time.sleep(0.5)
    capture_mode("dark", "assets/screenshots/dark_mode.png")
    save_settings({"theme": "light"})
    print("Screenshots retaken successfully!")


if __name__ == "__main__":
    main()
