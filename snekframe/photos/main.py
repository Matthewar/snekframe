"""Top Level Photo Page"""

from enum import Enum, auto

from tkinter import ttk

from .. import elements, db
from ..settings import SettingsWindow, SettingsContainer
from ..params import WINDOW_WIDTH, WINDOW_HEIGHT, TITLE_BAR_HEIGHT
from .title import PhotoTitleBar, VoltageWarningWindow
from .container import PhotoContainer
from .display import PhotoDisplayWindow
from .gallery import PhotoGalleryWindow

class PhotoWindow:
    """Photo window is made of 3 photos so they don't have to be loaded while the photos are dragged"""

    class OpenWindow(Enum):
        Gallery = auto()
        Display = auto()
        Settings = auto()
        LowVoltageWarning = auto()

    def __init__(self, frame):
        self._window = frame

        db.startup.initialise_runtimes()

        self._settings = SettingsContainer()
        self._photos = PhotoContainer(self._settings.shuffle_photos)

        self._title_bar = PhotoTitleBar(self._window, self._photos, self._open_slideshow_window, self._open_photo_gallery, self._open_settings, self._open_voltage_warning)

        self._gallery_window = None
        self._display_window = None
        self._settings_window = None
        self._voltage_warning_window = None

        self._gallery_regenerate_required = False

        self._current_window = None

        if not self._photos.photos_selected:
            self._title_bar.invoke_gallery_button()
        else:
            self._open_slideshow_window()

    def place(self, **place_kwargs):
        self._window.place(**place_kwargs)

    def _close_current_window(self):
        if self._current_window is None:
            return # Skip, should only occur on startup
        if self._current_window == self.OpenWindow.Gallery:
            assert self._gallery_window is not None
            self._gallery_window.place_forget()
        elif self._current_window == self.OpenWindow.Display:
            assert self._display_window is not None
            self._display_window.place_forget()
        elif self._current_window == self.OpenWindow.Settings:
            assert self._settings_window is not None
            self._settings_window.place_forget()
        elif self._current_window == self.OpenWindow.LowVoltageWarning:
            assert self._voltage_warning_window is not None
            self._voltage_warning_window.place_forget()
        else:
            raise TypeError()

        self._current_window = None

    def _open_photo_gallery(self):
        if not self._title_bar.visible:
            self._title_bar.place()
        self._close_current_window()

        if self._gallery_window is None:
            self._gallery_window = PhotoGalleryWindow(self._window, self._photos, self._callback_change_slideshow_window)
        self._gallery_window.place(x=0, y=TITLE_BAR_HEIGHT, anchor="nw", width=WINDOW_WIDTH, height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT)
        self._current_window = self.OpenWindow.Gallery

    def _callback_change_slideshow_window(self):
        self._gallery_regenerate_required = True

    def _open_slideshow_window(self):
        # TODO: Regenerate if settings change (rescan done)
        if self._title_bar.visible:
            self._title_bar.place_forget()
        self._close_current_window()

        if self._display_window is None:
            self._display_window = PhotoDisplayWindow(self._window, self._settings, self._title_bar.place, self._title_bar.place_forget)
        elif self._gallery_regenerate_required:
            self._display_window.regenerate_window()

        #if self._selection.all_photos_selected:
        #    self._title_bar.display_photo_title("All Photos")
        #else:
        #    self._title_bar.display_photo_title(self._selection.album)
        self._title_bar.display_photo_title("Slideshow")

        self._display_window.place(x=0, y=0, anchor="nw")
        self._current_window = self.OpenWindow.Display

    #def _regenerate_slideshow(self):
    def _destroy_photo_window(self, display_window=True, selection_window=True): # TODO
        if self._display_window is not None and display_window:
            self._display_window.place_forget()
            del self._display_window
            self._display_window = None
        if self._gallery_window is not None and selection_window:
            self._gallery_window.place_forget()
            del self._gallery_window
            self._gallery_window = None

    def _open_settings(self):
        if not self._title_bar.visible:
            self._title_bar.place()
        self._close_current_window()

        if self._settings_window is None:
            # TODO: Need to be able to exit to previous window from here
            self._settings_window = SettingsWindow(self._window, self._photos, self._settings, self._destroy_photo_window)
        self._settings_window.place(x=0, y=TITLE_BAR_HEIGHT, anchor="nw", width=WINDOW_WIDTH, height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT)
        self._current_window = self.OpenWindow.Settings

    def _open_voltage_warning(self):
        if not self._title_bar.visible:
            self._title_bar.place()
        self._close_current_window()

        if self._voltage_warning_window is None:
            self._voltage_warning_window = VoltageWarningWindow(self._window)
        self._voltage_warning_window.place(x=0, y=TITLE_BAR_HEIGHT, anchor="nw", width=WINDOW_WIDTH, height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT)
        self._current_window = self.OpenWindow.LowVoltageWarning
