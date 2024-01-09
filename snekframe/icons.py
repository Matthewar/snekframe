import importlib.resources
import io

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

import PIL

from . import images

def _svg_to_png(infile, outfile):
    drawing = svg2rlg(infile)
    print(drawing)
    renderPM.drawToFile(drawing, outfile, fmt="PNG") # bg=0x

def _svg_to_photoimage(infile): #, size):
    bytes_png = io.BytesIO()
    _svg_to_png(infile, bytes_png)

    image = PIL.Image.open(bytes_png)
    return image

class _Icons:
    _IMAGE_FILES = {
        "plus": "add.svg",
        "minus": "remove.svg",
        "settings": "settings.svg",
        "slideshow": "slideshow.svg",
        "shuffle": "shuffle.svg",
    }
    _IMAGE_BASE_PATH = importlib.resources.files(images)

    def __init__(self):
        self._images = {}

    def get(self, key):
        """Get image"""
        if key not in self._IMAGE_FILES:
            raise AttributeError(f"No known image file for '{key}'")

        if key not in self._images:
            filepath = self._IMAGE_BASE_PATH / self._IMAGE_FILES[key]
            self._images[key] = PIL.ImageTk.PhotoImage(_svg_to_photoimage(filepath))

        return self._images[key]

ICONS = _Icons()
