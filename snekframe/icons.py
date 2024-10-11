import importlib.resources
import io

from svglib import svglib
import reportlab.graphics.renderPM

import PIL

from . import images
from . import styles

_DEFAULT_PATHCOLOUR = styles.Colour(0x000000)
_DEFAULT_BACKGROUND = styles.Colour(0xffffff)

def _svg_to_png(infile, outfile, pathcolour=_DEFAULT_PATHCOLOUR, background=_DEFAULT_BACKGROUND):
    """Converts SVG file to PNG

    Assumes single colour SVG
    """
    drawing = svglib.svg2rlg(infile, color_converter=lambda colour_in: reportlab.lib.colors.HexColor(pathcolour.string))
    reportlab.graphics.renderPM.drawToFile(drawing, outfile, fmt="PNG", bg=background.integer)

def _svg_to_photoimage(infile, pathcolour=_DEFAULT_PATHCOLOUR, background=_DEFAULT_BACKGROUND): #, size):
    bytes_png = io.BytesIO()
    _svg_to_png(infile, bytes_png, pathcolour=pathcolour, background=background)

    image = PIL.Image.open(bytes_png)
    return image

class _Icons:
    _IMAGE_FILES = {
        "plus": "add.svg",
        "minus": "remove.svg",
        "settings": "settings.svg",
        "slideshow": "slideshow.svg",
        "shuffle": "shuffle.svg",
        "photo": "photo.svg",
        "bolt": "bolt.svg",
        "system": "power_settings.svg",
        "display": "display_settings.svg",
        "photo_library": "photo_library.svg",
        "cross": "close.svg",
        "tick": "done.svg",
        "arrow_back": "arrow_back.svg",
        "arrow_forward": "arrow_forward.svg",
        "arrow_upward": "arrow_upward.svg",
        "empty_checkbox": "check_box_outline_blank.svg",
        "partial_checkbox": "check_box_mid.svg",
        "ticked_checkbox": "check_box.svg",
        "folder": "folder.svg",
    }
    _IMAGE_BASE_PATH = importlib.resources.files(images)

    def __init__(self):
        self._images = {}

    def get(self, key, pathcolour=_DEFAULT_PATHCOLOUR, background=_DEFAULT_BACKGROUND):
        """Get image"""
        if key not in self._IMAGE_FILES:
            raise AttributeError(f"No known image file for '{key}'")

        if key not in self._images:
            self._images[key] = {}

        hexcolour = (pathcolour.integer, background.integer)
        if hexcolour not in self._images[key]:
            filepath = self._IMAGE_BASE_PATH / self._IMAGE_FILES[key]
            self._images[key][hexcolour] = PIL.ImageTk.PhotoImage(_svg_to_photoimage(filepath, pathcolour=pathcolour, background=background))

        return self._images[key][hexcolour]

ICONS = _Icons()
