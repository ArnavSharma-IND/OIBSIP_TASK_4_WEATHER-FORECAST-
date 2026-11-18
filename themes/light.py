"""Light Theme configuration: Warm Beige + Burnt Orange.

Palette defined per project specifications:
Main Background:   #F3EDE3
Surface:           #FAF7F1
Secondary Surface: #E9DFD0
Primary Accent:    #C8793C
Primary Text:      #29251F
Secondary Text:    #81776A
Borders:           #DED5C9
"""

LIGHT_THEME = {
    "name": "light",
    "display_name": "Light Mode (Beige & Burnt Orange)",
    # Palette
    "bg": "#F3EDE3",
    "surface": "#FAF7F1",
    "surface_secondary": "#E9DFD0",
    "accent": "#C8793C",
    "accent_hover": "#B3682F",
    "accent_light": "#F7E8D8",
    "accent_text": "#FFFFFF",
    "text_primary": "#29251F",
    "text_secondary": "#81776A",
    "border": "#DED5C9",
    "border_subtle": "#E5DCD0",
    "input_bg": "#FAF7F1",
    "input_fg": "#29251F",
    "input_border": "#DED5C9",
    "card_bg": "#FAF7F1",
    # Status alerts
    "error_bg": "#FBEAE8",
    "error_fg": "#C53030",
    "error_border": "#F5C6CB",
    "success_bg": "#E8F5E9",
    "success_fg": "#2E7D32",
    # Typography
    "font_family": "Segoe UI",  # High-quality cross-platform system font with fallback
    "font_title": ("Segoe UI", 24, "bold"),
    "font_temp_hero": ("Segoe UI", 56, "bold"),
    "font_temp_sub": ("Segoe UI", 28, "normal"),
    "font_subtitle": ("Segoe UI", 16, "normal"),
    "font_section": ("Segoe UI", 11, "bold"),
    "font_body": ("Segoe UI", 10, "normal"),
    "font_body_bold": ("Segoe UI", 10, "bold"),
    "font_caption": ("Segoe UI", 8, "normal"),
    "font_caption_bold": ("Segoe UI", 8, "bold"),
}
