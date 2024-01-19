"""Gallery Page

Allows user to select photos and view them
"""

import tkinter as tk
from tkinter import ttk

from .. import elements, params
from ..fonts import FONTS

class GalleryAlbumButtons(elements.LimitedFrameBaseElement):
    def __init__(self, parent, previous_page, up_page, next_page):
        super().__init__(parent, {})

        self._previous_page = elements.IconButton(self._frame, previous_page, "arrow_back", enabled=False, style="Subtitle")
        self._previous_page.grid(row=0, column=0, padx=(25, 10))

        self._up_page = elements.IconButton(self._frame, up_page, "arrow_upward", enabled=False, style="Subtitle")
        self._up_page.grid(row=0, column=1, padx=(15, 10))

        self._next_page = elements.IconButton(self._frame, next_page, "arrow_forward", enabled=False, style="Subtitle")
        self._next_page.grid(row=0, column=2, padx=(15, 0))

    def set_button_enables(self, back=None, up=None, forward=None):
        if back is not None:
            self._previous_page.enabled = back
        if up is not None:
            self._up_page.enabled = up
        if forward is not None:
            self._next_page.enabled = forward

class GallerySelectButtons(elements.LimitedFrameBaseElement):
    def __init__(self, parent, photo_selection, start_selection_mode, end_selection_mode):
        super().__init__(parent, {})

        self._photo_selection = photo_selection
        self._start_selection_callback = start_selection_mode
        self._end_selection_callback = end_selection_mode

        column = 0

        self._select_all_button = elements.IconToggleButton(self._frame, photo_selection.select_all_photos, photo_selection.select_no_photos, icon_name="check_box_outline_blank", selected_icon_name="check_box", enabled=False, selected=False, style="Subtitle") # TODO: Support selected and disabled
        self._select_all_button.grid(row=0, column=column, padx=10)
        self._select_all_button.grid_remove()

        column += 1

        self._selection_button = elements.TextButton(self._frame, self._start_selection_mode, text="Select Photos", enabled=photo_selection.photos_available, style="Subtitle")
        self._selection_button.grid(row=0, column=column, padx=10)

        column += 1

        self._cancel_selection_button = elements.IconButton(self._frame, self._end_selection_mode(save=False), icon_name="cross", enabled=False, style="Subtitle")
        self._cancel_selection_button.grid(row=0, column=column, padx=10)
        self._cancel_selection_button.grid_remove()

        column += 1

        self._save_selection_button = elements.IconButton(self._frame, self._end_selection_mode(save=True), icon_name="tick", enabled=False, style="Subtitle")
        self._save_selection_button.grid(row=0, column=column, padx=10)
        self._save_selection_button.grid_remove()

        column += 1

    def _start_selection_mode(self):
        self._selection_button.enabled = False
        self._start_selection_callback()
        self._select_all_button.enabled = True
        self._select_all_button.selected = self._photo_selection.all_photos_selected
        self._cancel_selection_button.enabled = True
        self._save_selection_button.enabled = True

        self._selection_button.grid_remove()
        self._select_all_button.grid()
        self._cancel_selection_button.grid()
        self._save_selection_button.grid()

    def _end_selection_mode(self, save=None):
        if not isinstance(save, bool):
            raise TypeError()

        self._selection_button.grid()
        self._select_all_button.grid_remove()
        self._cancel_selection_button.grid_remove()
        self._save_selection_button.grid_remove()

        self._select_all_button.selected = False # TODO: Can't be selected and disabled
        self._select_all_button.enabled = False
        self._cancel_selection_button.enabled = False
        self._save_selection_button.enabled = False
        self._end_selection_callback()
        self._selection_button.enabled = True

class GalleryTitleBar(elements.LimitedFrameBaseElement): # TODO: Rename styles
    """Gallery options"""
    def __init__(self, parent, previous_page, up_page, next_page, photo_selection, start_selection_mode, end_selection_mode):
        super().__init__(parent, {})

        self._album_buttons = GalleryAlbumButtons(self._frame, previous_page, up_page, next_page)
        self._album_buttons.place(relx=0, rely=0.5, anchor="w")

        self._title = elements.UpdateLabel(self._frame, initialtext="All Photos", style="Subtitle")
        self._title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._select_buttons = GallerySelectButtons(self._frame, photo_selection, start_selection_mode, end_selection_mode)
        self._select_buttons.place(relx=1.0, rely=0.5, anchor="e")

    @property
    def title(self):
        return self._title.text

    @title.setter
    def title(self, value):
        self._title.text = value

    def set_button_enables(self, *args, **kwargs):
        return self._album_buttons.set_button_enables(*args, **kwargs)

class NoPhotosPage(elements.LimitedFrameBaseElement):
    def __init__(self, parent : ttk.Frame):
        super().__init__(parent, {})

        rows = (
            ttk.Label(self._frame, text="No Photos Available", font=FONTS.title),
            ttk.Label(self._frame, text="Go to settings to scan for photos", font=FONTS.subtitle)
        )

        for row, element in enumerate(rows, start=1):
            element.grid(row=row, column=1)

        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_columnconfigure(2, weight=1)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(len(rows), weight=1)

class PhotoGalleryPage(elements.LimitedFrameBaseElement):
    _NUM_ROWS = params.NUM_ROWS_PER_GALLERY_PAGE
    _NUM_COLUMNS = params.NUM_ITEMS_PER_GALLERY_ROW

    @classmethod
    def get_photos_per_page(cls):
        return cls._NUM_ROWS * cls._NUM_COLUMNS
