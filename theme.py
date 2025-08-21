# theme.py

import tkinter as tk
from tkinter import ttk

# --- Color Palette ---
DARK_BACKGROUND = "#2e2e2e"
DARK_FOREGROUND = "#dcdcdc"
DARK_MID_TONE = "#4f4f4f"
DARK_ENTRY_BG = "#3c3c3c"
BLUE_ACCENT = "#5a9cf8"
WHITE = "#ffffff"

def setup_theme(app):
    """
    Initializes and configures the ttk theme for the application.
    This function defines a custom dark theme and sets it as the default.
    """
    style = ttk.Style(app)

    # --- Create the Dark Theme ---
    # Using the 'clam' theme as a base for customization.
    style.theme_create("dark_theme", parent="clam", settings={
        ".": {
            "configure": {
                "background": DARK_BACKGROUND,
                "foreground": DARK_FOREGROUND,
                "bordercolor": "#555555",
                "darkcolor": DARK_BACKGROUND,
                "lightcolor": DARK_MID_TONE,
                "troughcolor": DARK_ENTRY_BG,
                "selectbackground": BLUE_ACCENT,
                "selectforeground": WHITE
            }
        },
        "TButton": {
            "configure": {"background": DARK_MID_TONE, "foreground": DARK_FOREGROUND, "padding": 5, "relief": "flat", "borderwidth": 1},
            "map": {"background": [("active", BLUE_ACCENT), ("disabled", DARK_ENTRY_BG)], "foreground": [("active", WHITE)]}
        },
        "TEntry": {
            "configure": {"fieldbackground": DARK_ENTRY_BG, "foreground": DARK_FOREGROUND, "insertcolor": WHITE, "borderwidth": 1, "relief": "flat"}
        },
        "TCombobox": {
            "configure": {"fieldbackground": DARK_ENTRY_BG, "background": DARK_MID_TONE, "foreground": DARK_FOREGROUND, "arrowcolor": DARK_FOREGROUND},
            "map": {"background": [("readonly", DARK_MID_TONE)], "fieldbackground": [("readonly", DARK_ENTRY_BG)], "foreground": [("readonly", DARK_FOREGROUND)]}
        },
        "TLabel": {"configure": {"background": DARK_BACKGROUND, "foreground": DARK_FOREGROUND}},
        "TFrame": {"configure": {"background": DARK_BACKGROUND}},
        "Treeview": {
            "configure": {"background": DARK_ENTRY_BG, "fieldbackground": DARK_ENTRY_BG, "foreground": DARK_FOREGROUND},
            "map": {"background": [("selected", BLUE_ACCENT)], "foreground": [("selected", WHITE)]}
        },
        "Treeview.Heading": {
            "configure": {"background": DARK_MID_TONE, "foreground": DARK_FOREGROUND, "relief": "flat"},
            "map": {"background": [("active", BLUE_ACCENT)]}
        },
        "Vertical.TScrollbar": {
            "configure": {"background": DARK_MID_TONE, "troughcolor": DARK_ENTRY_BG, "bordercolor": "#555555", "arrowcolor": DARK_FOREGROUND},
            "map": {"background": [("active", BLUE_ACCENT)]}
        },
        "TLabelframe": {"configure": {"background": DARK_BACKGROUND, "foreground": DARK_FOREGROUND}},
        "TLabelframe.Label": {"configure": {"background": DARK_BACKGROUND, "foreground": DARK_FOREGROUND}},
        "TCheckbutton": {
            "configure": {"background": DARK_BACKGROUND, "foreground": DARK_FOREGROUND},
            "map": {
                "background": [("active", DARK_BACKGROUND)],
                "indicatorbackground": [("!selected", DARK_MID_TONE), ("selected", BLUE_ACCENT)],
                "indicatorcolor": [("selected", WHITE)]
            }
        },
        "TPanedwindow": {"configure": {"background": DARK_BACKGROUND}}
    })

    # Set the dark theme as the default
    style.theme_use("dark_theme")
    app.configure(background=DARK_BACKGROUND)

def switch_theme(app, dark_mode: bool):
    """
    Switches the application's theme and updates core widgets.
    """
    style = app.style
    if dark_mode:
        style.theme_use("dark_theme")
        app.configure(background=DARK_BACKGROUND)
        bg, fg, abg, afg = DARK_BACKGROUND, DARK_FOREGROUND, BLUE_ACCENT, WHITE
    else:
        # Use the default 'clam' theme for a consistent light mode
        style.theme_use("clam")
        native_bg = style.lookup(".", "background")
        native_fg = style.lookup(".", "foreground")
        app.configure(background=native_bg)
        bg, fg, abg, afg = native_bg, native_fg, style.lookup("TButton", "selectbackground"), style.lookup("TButton", "selectforeground")

    # --- Update Menu Colors ---
    # The menu widget is part of the core tk library, so it must be configured manually.
    app.menubar.config(bg=bg, fg=fg, activebackground=abg, activeforeground=afg, relief="flat")
    # Iterate through each cascade menu and apply the theme
    for i in range(app.menubar.index("end") + 1):
        try:
            menu = app.menubar.nametowidget(app.menubar.entrycget(i, "menu"))
            menu.config(bg=bg, fg=fg, activebackground=abg, activeforeground=afg, relief="flat")
        except (tk.TclError, AttributeError):
            # This handles separators or non-cascade menu items
            pass

    # --- Update Canvas Background ---
    # The Canvas is also a core tk widget.
    if hasattr(app, 'properties_canvas'):
        canvas_bg = style.lookup("TFrame", "background")
        app.properties_canvas.config(bg=canvas_bg)