from tkinter import font

class _FontGenerator:
    def __init__(self):
        self._fonts = {}

    def __getattr__(self, key):
        font = self._fonts.get(key)
        if key is None:
            raise AttributeError(f"Font '{key}' does not exist")
        return font

    _FONT_FAMILY = "Helvetica"

    def generate(self):
        self._fonts["title"] = font.Font(name="TitleFont", family=self._FONT_FAMILY, size=30, weight="bold")
        self._fonts["subtitle"] = font.Font(name="SubtitleFont", family=self._FONT_FAMILY, size=20, weight="bold")
        self._fonts["default"] = font.Font(name="DefaultFont", family=self._FONT_FAMILY, size=13)

FONTS = _FontGenerator()
