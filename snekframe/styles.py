import tkinter.ttk as ttk
import reportlab.lib.colors

class Colour:
    def __init__(self, colour):
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
    def string(self):
        """Get hex colour as a string

        Prefixed with '#'
        """
        return f"#{self._colour:x}"

    @property
    def integer(self):
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

class _StyleGenerator:
    def generate(self):
        styles = ttk.Style()
        styles.configure("TFrame", background=DEFAULT_BACKGROUND_COLOUR.string)
        styles.configure("TLabel", background=DEFAULT_BACKGROUND_COLOUR.string)
        styles.configure("TButton", background=HIGHLIGHT_BACKGROUND_COLOUR, foreground=FONT_COLOUR.string)
        styles.configure("DisplayWindow.TFrame", background=PHOTO_BACKGROUND_COLOUR.string)
        styles.configure("Image.DisplayWindow.TLabel", background=PHOTO_BACKGROUND_COLOUR.string)
        styles.configure("TitleBar.TFrame", background=HIGHLIGHT_BACKGROUND_COLOUR.string)
        styles.configure("TitleBar.TLabel", background=HIGHLIGHT_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string)
        styles.configure("TitleBar.TButton", background=DEFAULT_BACKGROUND_COLOUR.string, foreground=FONT_COLOUR.string)
        styles.configure("TButton", font="DefaultFont")

STYLES = _StyleGenerator()
