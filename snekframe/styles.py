from typing import Optional

import tkinter.ttk as ttk
import reportlab.lib.colors

class Colour:
    def __init__(self, colour : str | int):
        if isinstance(colour, str):
            if colour[0] == '#':
                colour_value = colour[1:]
            else:
                colour_value = colour
            self._colour = int(colour_value, 16)
        elif isinstance(colour, int):
            self._colour = colour
        else:
            raise TypeError("Expecting colour as a string or integer value")

    @property
    def string(self) -> str:
        """Get hex colour as a string

        Prefixed with '#'
        """
        return f"#{self._colour:0<6x}"

    @property
    def integer(self) -> int:
        """Get hex colour as an integer"""
        return self._colour

    @property
    def reportlab_hex(self):
        """Get hex colour as a reportlab.lib.colors.HexColor"""
        return reportlab.lib.colors.HexColor(self.string)

DEFAULT_BACKGROUND_COLOUR = Colour(0x64676E)
HIGHLIGHT_BACKGROUND_COLOUR = Colour(0x2E3033)
PHOTO_BACKGROUND_COLOUR = Colour("0x000000") # Black
FONT_COLOUR = Colour(0xffffff) # White
DISABLED_COLOUR = Colour(0xabb0b8)
SUBTITLE_BACKGROUND_COLOUR = Colour(0x58595C)

def _append_style_name(base_style : str, style_name : Optional[str]) -> str:
    """Helper function to build a style name"""
    if style_name is None:
        return base_style
    return f"{style_name}.{base_style}"

def get_label_style_name(style_name : Optional[str]) -> str:
    """Get style built on default label style"""
    return _append_style_name("TLabel", style_name)

def get_frame_style_name(style_name : str) -> str:
    """Get style built on default frame style"""
    return _append_style_name("TFrame", style_name)

_ICON_STYLES = {
    "Default.Icon.Button.TLabel": {
        "background": DEFAULT_BACKGROUND_COLOUR,
        "pathcolour": HIGHLIGHT_BACKGROUND_COLOUR,
    },
    "Active.Default.Icon.Button.TLabel": {
        "background": DEFAULT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
    "Disabled.Default.Icon.Button.TLabel": {
        "background": DEFAULT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0x000000),
    },
    "Selected.Default.Icon.Button.TLabel": {
        "background": DEFAULT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xabb0b8),
    },
    "Title.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xabb0b8),
    },
    "Active.Title.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
    "Disabled.Title.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0x000000),
    },
    "Selected.Title.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
    "Voltage.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xff0000),
    },
    "Active.Voltage.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
    "Disabled.Voltage.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0x000000),
    },
    "Selected.Voltage.Icon.Button.TLabel": {
        "background": HIGHLIGHT_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
    "Default.IconText.Button.TLabel": {
        "background": DEFAULT_BACKGROUND_COLOUR,
        "pathcolour": HIGHLIGHT_BACKGROUND_COLOUR,
    },
    "Active.Default.IconText.Button.TLabel": {
        "background": Colour(0xffffff),
        "pathcolour": HIGHLIGHT_BACKGROUND_COLOUR,
    },
    "Disabled.Default.IconText.Button.TLabel": {
        "background": Colour(0x000000),
        "pathcolour": HIGHLIGHT_BACKGROUND_COLOUR,
    },
    "Selected.Default.IconText.Button.TLabel": {
        "background": Colour(0xffffff),
        "pathcolour": HIGHLIGHT_BACKGROUND_COLOUR,
    },
    "SubTitleBar.Icon.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xabb0b8),
    },
    "Active.SubTitleBar.Icon.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
    "Disabled.SubTitleBar.Icon.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0x000000),
    },
    "Selected.SubTitleBar.Icon.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },

    "GalleryItem.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xabb0b8),
    },
    "Active.GalleryItem.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
    "Disabled.GalleryItem.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0x000000),
    },
    "Selected.GalleryItem.Button.TLabel": {
        "background": SUBTITLE_BACKGROUND_COLOUR,
        "pathcolour": Colour(0xffffff),
    },
}

class _StyleGenerator:
    def generate(self):
        styles = ttk.Style()
        styles.configure("TFrame", background=DEFAULT_BACKGROUND_COLOUR.string)
        styles.configure("TLabel", background=DEFAULT_BACKGROUND_COLOUR.string, foreground="#000000", font="DefaultFont")
        styles.configure("TButton", background=HIGHLIGHT_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string, font="DefaultFont")

        styles.configure("Default.Button.TFrame", background=HIGHLIGHT_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string)
        styles.configure("Active.Default.Button.TFrame", background="#ffffff")
        styles.configure("Disabled.Default.Button.TFrame", background="#000000")
        styles.configure("Selected.Default.Button.TFrame", background="#ffffff", foreground="#000000")

        styles.configure("Default.Button.TLabel", background=HIGHLIGHT_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string)
        styles.configure("Active.Default.Button.TLabel", background="#ffffff")
        styles.configure("Disabled.Default.Button.TLabel", background="#000000")
        styles.configure("Selected.Default.Button.TLabel", background="#ffffff", foreground="#000000")

        styles.configure("Default.Icon.Button.TLabel", background=DEFAULT_BACKGROUND_COLOUR.string)
        styles.configure("Title.Icon.Button.TLabel", background=HIGHLIGHT_BACKGROUND_COLOUR.string)
        styles.configure("Voltage.Icon.Button.TLabel", background=HIGHLIGHT_BACKGROUND_COLOUR.string)

        styles.configure("Default.IconText.Button.TLabel", background=DEFAULT_BACKGROUND_COLOUR.string)
        styles.configure("Active.Default.IconText.Button.TLabel", background=Colour(0xffffff).string)
        styles.configure("Disabled.Default.IconText.Button.TLabel", background=Colour(0x000000).string)
        styles.configure("Selected.Default.IconText.Button.TLabel", background=Colour(0xffffff).string, foreground=Colour(0xabb0b8).string)
        styles.configure("Default.IconText.Button.TFrame", background=DEFAULT_BACKGROUND_COLOUR.string)
        styles.configure("Active.Default.IconText.Button.TFrame", background=Colour(0xffffff).string)
        styles.configure("Disabled.Default.IconText.Button.TFrame", background=Colour(0x000000).string)
        styles.configure("Selected.Default.IconText.Button.TFrame", background=Colour(0xffffff).string, foreground="#abb0b8")

        styles.configure("GalleryItem.Button.TLabel", background=SUBTITLE_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string)
        styles.configure("Active.GalleryItem.Button.TFrame", background="#ffffff")
        #styles.configure("Disabled.GalleryItem.Button.TFrame", background="#000000")
        #styles.configure("Selected.GalleryItem.Button.TFrame", background="#ffffff", foreground="#000000")

        styles.configure("DisplayWindow.TFrame", background=PHOTO_BACKGROUND_COLOUR.string)
        styles.configure("Image.DisplayWindow.TLabel", background=PHOTO_BACKGROUND_COLOUR.string)
        styles.configure("TitleBar.TFrame", background=HIGHLIGHT_BACKGROUND_COLOUR.string)
        styles.configure("TitleBar.TLabel", background=HIGHLIGHT_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string)

        styles.configure("SubTitleBar.TFrame", background=SUBTITLE_BACKGROUND_COLOUR.string)
        styles.configure("SubTitleBar.TLabel", background=SUBTITLE_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string)

STYLES = _StyleGenerator()
