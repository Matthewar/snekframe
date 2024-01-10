import tkinter.ttk as ttk

DEFAULT_BACKGROUND_COLOUR = "#64676E"
HIGHLIGHT_BACKGROUND_COLOUR = "#2E3033"
PHOTO_BACKGROUND_COLOUR = "#000000" # Black
FONT_COLOUR = "#ffffff" # White

class _StyleGenerator:
    def generate(self):
        styles = ttk.Style()
        styles.configure("TFrame", background=DEFAULT_BACKGROUND_COLOUR)
        styles.configure("TLabel", background=DEFAULT_BACKGROUND_COLOUR)
        styles.configure("TButton", background=HIGHLIGHT_BACKGROUND_COLOUR, foreground=FONT_COLOUR)
        styles.configure("DisplayWindow.TFrame", background=PHOTO_BACKGROUND_COLOUR)
        styles.configure("Image.DisplayWindow.TLabel", background=PHOTO_BACKGROUND_COLOUR)
        styles.configure("TitleBar.TFrame", background=HIGHLIGHT_BACKGROUND_COLOUR)
        styles.configure("TitleBar.TLabel", background=HIGHLIGHT_BACKGROUND_COLOUR, foreground=FONT_COLOUR)
        styles.configure("TitleBar.TButton", background=DEFAULT_BACKGROUND_COLOUR, foreground=FONT_COLOUR)
        styles.configure("TButton", font="DefaultFont")

STYLES = _StyleGenerator()
