"""Main entry point for the Weather & Forecast desktop application.

Developed by Arnav Sharma.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

from config import APP_AUTHOR, APP_NAME, APP_VERSION
from modules.main_window import MainWindow
from utils.logger import app_logger


def main() -> None:
    """Initialize and run application."""
    app_logger.info("Starting %s v%s by %s", APP_NAME, APP_VERSION, APP_AUTHOR)

    try:
        app = MainWindow()
        app.mainloop()
    except KeyboardInterrupt:
        app_logger.info("Application closed by user interrupt.")
        sys.exit(0)
    except Exception as e:
        app_logger.critical("Fatal application crash: %s", e, exc_info=True)
        try:
            messagebox.showerror(
                "Fatal Error",
                f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check application.log for technical details.",
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
