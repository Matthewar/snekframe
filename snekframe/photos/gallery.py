"""Gallery Page

Allows user to select photos and view them
"""

from enum import Enum, auto
from typing import List, Optional
import os.path

import tkinter as tk
from tkinter import ttk

from .. import elements, params, styles
from ..fonts import FONTS
from ..icons import ICONS
from ..params import WINDOW_WIDTH, WINDOW_HEIGHT, TITLE_BAR_HEIGHT
from .container import _FileSystemExplorer, PageDirection, ViewUpdate, ItemViewUpdate, NameViewUpdate, SelectViewUpdate, DirectionsUpdate, FullImageViewUpdate
from . import container

class GalleryAlbumButtons(elements.LimitedFrameBaseElement):
    def __init__(self, parent, previous_page, up_page, next_page):
        super().__init__(parent, {}, style="SubTitleBar")

        def get_callback(pagechange_callback):
            def button_callback():
                self.set_button_enables(back=False, up=False, forward=False)
                pagechange_callback()
            return button_callback

        self._previous_page = elements.IconButton(self._frame, get_callback(previous_page), "arrow_back", enabled=False, style="SubTitleBar")
        self._previous_page.grid(row=0, column=0, padx=(25, 10))

        self._up_page = elements.IconButton(self._frame, get_callback(up_page), "arrow_upward", enabled=False, style="SubTitleBar")
        self._up_page.grid(row=0, column=1, padx=(15, 10))

        self._next_page = elements.IconButton(self._frame, get_callback(next_page), "arrow_forward", enabled=False, style="SubTitleBar")
        self._next_page.grid(row=0, column=2, padx=(15, 0))

    def set_button_enables(self, back=None, up=None, forward=None):
        if back is not None:
            self._previous_page.enabled = back
        if up is not None:
            self._up_page.enabled = up
        if forward is not None:
            self._next_page.enabled = forward

class GallerySelectButtons(elements.LimitedFrameBaseElement):
    def __init__(self, parent, photos_container, start_selection_mode, end_selection_mode, select_all_photos, select_no_photos):
        super().__init__(parent, {}, style="SubTitleBar")

        self._photos_container = photos_container

        self._start_selection_callback = start_selection_mode
        self._end_selection_callback = end_selection_mode

        column = 0

        self._select_all_button = elements.CheckBoxButton(self._frame, select_all_photos, select_no_photos, enabled=False, selected=elements.CheckBoxSelection.Unselected, style="SubTitleBar")
        self._select_all_button.grid(row=0, column=column, padx=10)
        self._select_all_button.grid_remove()

        column += 1

        self._selection_button = elements.TextButton(self._frame, self._start_selection_mode, text="Select Photos", enabled=photos_container.num_photos > 0, style="SubTitleBar")
        self._selection_button.grid(row=0, column=column, padx=10)

        column += 1

        self._cancel_selection_button = elements.IconButton(self._frame, lambda: self._end_selection_mode(save=False), icon_name="cross", enabled=False, style="SubTitleBar")
        self._cancel_selection_button.grid(row=0, column=column, padx=10)
        self._cancel_selection_button.grid_remove()

        column += 1

        self._save_selection_button = elements.IconButton(self._frame, lambda: self._end_selection_mode(save=True), icon_name="tick", enabled=False, style="SubTitleBar")
        self._save_selection_button.grid(row=0, column=column, padx=10)
        self._save_selection_button.grid_remove()

        column += 1

    def set_button_enables(self, select_all=None, open_selection_mode=None):
        if select_all is not None:
            self._select_all_button.selected = select_all
        if open_selection_mode is not None:
            if self._save_selection_button.enabled:
                # Already in selection mode, shouldn't be changing this
                self._selection_button.enabled = open_selection_mode

    def _start_selection_mode(self):
        self._selection_button.enabled = False
        self._start_selection_callback()
        self._select_all_button.enabled = True
        if self._photos_container.all_photos_selected:
            self._select_all_button.selected = elements.CheckBoxSelection.Selected
        elif self._photos_container.num_selected_photos == 0:
            self._select_all_button.selected = elements.CheckBoxSelection.Unselected
        else:
            self._select_all_button.selected = elements.CheckBoxSelection.PartialSelect
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

        self._select_all_button.enabled = False
        self._cancel_selection_button.enabled = False
        self._save_selection_button.enabled = False
        self._end_selection_callback(save=save)
        self._selection_button.enabled = True

class GalleryTitleBar(elements.LimitedFrameBaseElement): # TODO: Rename styles
    """Gallery options"""
    def __init__(self, parent, previous_page, up_page, next_page, photos_container, start_selection_mode, end_selection_mode, select_all_photos, select_no_photos):
        super().__init__(parent, {}, style="SubTitleBar")

        self._album_buttons = GalleryAlbumButtons(self._frame, previous_page, up_page, next_page)
        self._album_buttons.place(relx=0, rely=0.5, anchor="w")

        self._title = elements.UpdateLabel(self._frame, initialtext="All Photos", style="SubTitleBar")
        self._title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._select_buttons = GallerySelectButtons(self._frame, photos_container, start_selection_mode, end_selection_mode, select_all_photos, select_no_photos)
        self._select_buttons.place(relx=1.0, rely=0.5, anchor="e")

    @property
    def title(self):
        return self._title.text

    @title.setter
    def title(self, value):
        self._title.text = value

    def set_button_enables(self, back=None, up=None, forward=None, select_all=None, open_selection_mode=None):
        self._album_buttons.set_button_enables(back=back, up=up, forward=forward)
        self._select_buttons.set_button_enables(select_all=select_all, open_selection_mode=open_selection_mode)

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

class _PhotoGalleryItemButton(elements._Button):
    def __init__(self, parent, command, enabled=True, album_text=None, photo_text=None, **label_kwargs):
        if (album_text is not None) == (photo_text is not None):
            raise TypeError()

        self._style = "GalleryItem.Button.TLabel"
        self._album_icon_inactive = ICONS.get("folder", **styles._ICON_STYLES[self._style])
        self._album_icon_active = ICONS.get("folder", **styles._ICON_STYLES[f"Active.{self._style}"])
        self._album_mode = album_text is not None
        self._text= tk.StringVar()

        super().__init__(parent, ttk.Label, command, label_kwargs, enabled=enabled, compound="center", justify=tk.CENTER, anchor=tk.CENTER, textvariable=self._text, style=self._style)

        if album_text is not None:
            self.set_album_text(album_text)
        elif photo_text is not None:
            self.set_photo_text(photo_text)

    def _style_initial(self):
        """Overriding because this is handled in our constructor"""
        pass

    def _style_normal(self):
        if self._album_mode:
            self._element.configure(image=self._album_icon_inactive)
            self._element.image = self._album_icon_inactive
        self._element.configure(style=self._style)

    def _style_active(self):
        if self._album_mode:
            self._element.configure(image=self._album_icon_active)
            self._element.image = self._album_icon_active
        self._element.configure(style=f"Active.{self._style}")

    def _style_disabled(self):
        self._style_normal()

    def set_album_text(self, album_text):
        """Switch button to album"""
        self._album_mode = True
        self._element.configure(image=self._album_icon_inactive)
        self._element.image = self._album_icon_inactive
        self._text.set(album_text)

    def set_photo_text(self, photo_text):
        """Switch button to photo"""
        self._album_mode = False
        self._element.configure(image="")
        self._element.image = ""
        self._text.set(photo_text)

class _PhotoGalleryItem(elements.LimitedFrameBaseElement):
    """Single button for a photo or album"""
    def __init__(self, parent, open_command, select_command, unselect_command):
        super().__init__(parent, {})

        # Uses enabled to indicate hidden
        self._select_button = elements.CheckBoxButton(self._frame, select_command, unselect_command, enabled=False)

        self._open_button = _PhotoGalleryItemButton(self._frame, open_command, enabled=False, album_text="test")
        self._open_button.place(x=0, y=0, relwidth=1, relheight=1, anchor="nw")
        #self._open_button.place(x=0, y=0, anchor="nw")#relwidth=1, relheight=1, anchor="nw")

        self._selections_enabled = False

    def _show_button(self, album_text=None, photo_text=None, selection_mode=None):
        if self._open_button.enabled:
            return
        self._open_button.enabled = True
        if album_text is not None:
            self._open_button.set_album_text(album_text)
        elif photo_text is not None:
            self._open_button.set_photo_text(photo_text)
        if selection_mode is not None:
            self.selections_enabled = selection_mode

    def _hide_button(self):
        if not self._open_button.enabled:
            return
        self._open_button.enabled = False
        self._select_button.enabled = False

    def place(self, album_text=None, photo_text=None, selection_mode=None, **place_kwargs):
        self._show_button(album_text=album_text, photo_text=photo_text, selection_mode=selection_mode)
        super().place(**place_kwargs)

    def place_forget(self):
        self._hide_button()
        super().place_forget()

    def grid(self, album_text=None, photo_text=None, selection_mode=None, **grid_kwargs):
        self._show_button(album_text=album_text, photo_text=photo_text, selection_mode=selection_mode)
        super().grid(**grid_kwargs)
        self._open_button.place(x=0, y=0, relwidth=1, relheight=1, anchor="nw")

    def grid_remove(self):
        self._hide_button()
        super().grid_remove()

    @property
    def visible(self):
        """Whether the entire button is visible"""
        return self._open_button.enabled

    @property
    def selections_enabled(self):
        return self._select_button.enabled

    @selections_enabled.setter
    def selections_enabled(self, enable : bool):
        if self._selections_enabled and not enable:
            self._select_button.place_forget()
            self._selections_enabled = False
        elif not self._selections_enabled and enable:
            self._select_button.place(x=0, y=0, anchor="nw")
            self._select_button.tkraise()
            self._selections_enabled = True
            self._select_button.enabled = False
            self._select_button.selection = elements.CheckBoxSelection.PartialSelect

    @property
    def selection(self):
        if self._select_button.enabled:
            return self._select_button.selected
        return None

    @selection.setter
    def selection(self, select : container.PhotoDirectorySelection):
        if select == container.PhotoDirectorySelection.Not:
            self._select_button.selected = elements.CheckBoxSelection.Unselected
        elif select == container.PhotoDirectorySelection.Partial:
            self._select_button.selected = elements.CheckBoxSelection.PartialSelect
        elif select == container.PhotoDirectorySelection.All:
            self._select_button.selected = elements.CheckBoxSelection.Selected
        else:
            raise TypeError()
        if self._selections_enabled and not self._select_button.enabled:
            self._select_button.enabled = True

class PhotoGalleryPage(elements.LimitedFrameBaseElement):
    _NUM_ROWS = params.NUM_ROWS_PER_GALLERY_PAGE
    _NUM_COLUMNS = params.NUM_ITEMS_PER_GALLERY_ROW

    @classmethod
    def get_photos_per_page(cls):
        return cls._NUM_ROWS * cls._NUM_COLUMNS

    def __init__(self, parent, open_item, select_item, unselect_item, selections_enabled):
        super().__init__(parent, {})

        self._open_item_callback = open_item
        self._select_item_callback = select_item
        self._unselect_item_callback = unselect_item

        self._current_page_id = None

        row_phy_index = 0
        column_phy_index = 0

        self._frame.grid_rowconfigure(row_phy_index, weight=1)
        self._frame.grid_columnconfigure(column_phy_index, weight=1)

        self._labels : dict[int, dict[int, _PhotoGalleryItem]] = {}
        def _get_callback(func, index):
            return lambda: func(index)

        for row in range(self._NUM_ROWS):
            self._labels[row] = {}

            row_phy_index += 1
            self._frame.grid_rowconfigure(row_phy_index, weight=2)
            column_phy_index = 0

            for column in range(self._NUM_COLUMNS):
                index = row * 3 + column
                self._labels[row][column] = _PhotoGalleryItem(
                    self._frame,
                    _get_callback(self._open_item, index),
                    _get_callback(self._select_item, index),
                    _get_callback(self._unselect_item, index)
                )

                column_phy_index += 1
                if row == 0:
                    self._frame.grid_columnconfigure(column_phy_index, weight=2)

                self._labels[row][column].grid(row=row_phy_index, column=column_phy_index, sticky="snew")

                column_phy_index += 1
                if row == 0:
                    self._frame.grid_columnconfigure(column_phy_index, weight=1)

            row_phy_index += 1
            self._frame.grid_rowconfigure(row_phy_index, weight=1)

        self._selections_enabled = selections_enabled
        self.selections_enabled = selections_enabled

        self._frame.grid_propagate(False)

    def setup_new_page(self, page_id):
        """Reset page with new ID

        Begin redraw process
        """
        if self._current_page_id is not None:
            raise TypeError()

        self._current_page_id = page_id
        for row in self._labels.values():
            for item in row.values():
                item.grid_remove()

    @property
    def page_id(self):
        if self._current_page_id is None:
            raise TypeError()
        return self._current_page_id

    def disable_page(self):
        """Disable buttons"""
        self._current_page_id = None

        for row in self._labels.values():
            for item in row.values():
                item.enabled = False

    def place_forget(self):
        self.disable_page()
        super().place_forget()

    def grid_remove(self):
        self.disable_page()
        super().grid_remove()

    def update(self, info : ItemViewUpdate):
        if not isinstance(info, ItemViewUpdate):
            raise TypeError()
        if info.current_page_id != self._current_page_id:
            return

        row = info.index // 3
        column = info.index % 3

        if isinstance(info, NameViewUpdate):
            item_type = "album_text" if info.directory else "photo_text"
            self._labels[row][column].grid(selection_mode=self._selections_enabled, **{item_type: info.name})
        elif isinstance(info, SelectViewUpdate):
            self._labels[row][column].selection = info.selection
        else:
            raise TypeError()

    def set_select_all(self, selection : bool):
        if selection:
            item_selection = container.PhotoDirectorySelection.All
        else:
            item_selection = container.PhotoDirectorySelection.Not
        for row in self._labels.values():
            for item in row.values():
                item.selection = item_selection

    def _open_item(self, index):
        if self._current_page_id is None:
            return

        for row in self._labels.values():
            for item in row.values():
                item.enabled = False

        self._open_item_callback(self._current_page_id, index)

    def _select_item(self, index):
        if self._current_page_id is None:
            return

        self._select_item_callback(self._current_page_id, index)

    def _unselect_item(self, index):
        if self._current_page_id is None:
            return

        self._unselect_item_callback(self._current_page_id, index)

    @property
    def selections_enabled(self):
        return self._selections_enabled

    @selections_enabled.setter
    def selections_enabled(self, select : bool):
        self._selections_enabled = select
        for row in range(self._NUM_ROWS):
            for column in range(self._NUM_COLUMNS):
                self._labels[row][column].selections_enabled = select

class PhotoDisplayPage(elements.LimitedFrameBaseElement):
    def __init__(self, parent, select_item, unselect_item, selections_enabled):
        super().__init__(parent, {}, style="DisplayWindow")

        self._select_item_callback = select_item
        self._unselect_item_callback = unselect_item

        self._current_page_id = None
        self._image = None

        self._photo = ttk.Label(self._frame, text="Photo Loading", style="Image.DisplayWindow.TLabel")
        self._photo.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._select_button = elements.CheckBoxButton(self._frame, self._select_item, self._unselect_item, enabled=False)

        self.selections_enabled = selections_enabled

    def setup_new_page(self, page_id):
        if self._current_page_id is not None:
            raise TypeError()

        self._current_page_id = page_id

    @property
    def page_id(self):
        if self._current_page_id is None:
            raise TypeError()
        return self._current_page_id

    def disable_page(self):
        self._current_page_id = None

        self._image = None
        self._photo.configure(image="")
        self._photo.image = ""

    def place_forget(self):
        self.disable_page()
        super().place_forget()

    def grid_remove(self):
        self.disable_page()
        super().grid_remove()

    def update(self, info):
        if info.current_page_id != self._current_page_id:
            return

        if isinstance(info, FullImageViewUpdate):
            self._image = info.image
            self._photo.configure(image=info.image)
            self._photo.image = info.image
        elif isinstance(info, SelectViewUpdate):
            if info.selection == container.PhotoDirectorySelection.All:
                self._select_button.selected = elements.CheckBoxSelection.Selected
            elif info.selection == container.PhotoDirectorySelection.Not:
                self._select_button.selected = elements.CheckBoxSelection.Unselected
            else:
                raise TypeError()
        else:
            raise TypeError()

    def set_select_all(self, selection : bool):
        if selection:
            self._select_button.selected = elements.CheckBoxSelection.Selected
        else:
            self._select_button.selected = elements.CheckBoxSelection.Unselected

    def _select_item(self):
        if self._current_page_id is None:
            return

        self._select_item_callback(self._current_page_id, None)

    def _unselect_item(self):
        if self._current_page_id is None:
            return

        self._unselect_item_callback(self._current_page_id, None)

    @property
    def selections_enabled(self):
        return self._select_button.enabled

    @selections_enabled.setter
    def selections_enabled(self, enable : bool):
        if self._select_button.enabled and not enable:
            self._select_button.place_forget()
            self._select_button.enabled = False
        elif not self._select_button.enabled and enable:
            self._select_button.place(x=0, y=0, anchor="nw")
            self._select_button.tkraise()
            self._select_button.enabled = True

class PhotoGalleryWindow(elements.LimitedFrameBaseElement):
    """Displays all photos available

    Allows user to select which photos to display
    """
    def __init__(self, parent : ttk.Frame, photo_container : container.PhotoContainer, regenerate_slideshow): # TODO should pass width
        super().__init__(parent, {})

        self._photo_container = photo_container
        self._regenerate_slideshow = regenerate_slideshow

        self._title_bar = GalleryTitleBar(
            self._frame, self._goto_previous_page, self._goto_up_page, self._goto_next_page,
            self._photo_container, self._start_selection_mode, self._end_selection_mode,
            self._select_all_photos, self._select_no_photos
        )
        self._title_bar.place(x=0, y=0, width=WINDOW_WIDTH, height=TITLE_BAR_HEIGHT, anchor="nw")

        self._file_explorer = _FileSystemExplorer()
        self._update_view_job = None

        self._page_name : List[str] = []
        self._current_window = None
        self._gallery_loading_windows : List[PhotoGalleryPage] = [] # For loading directory pages
        self._display_loading_windows : List[PhotoDisplayPage] = [] # For loading display pages

        self._selection_mode = False

    def place(self, **place_kwargs):
        if self._photo_container.num_photos == 0:
            if isinstance(self._current_window, NoPhotosPage):
                pass
            elif isinstance(self._current_window, PhotoGalleryPage):
                self._gallery_loading_windows.append(self._current_window)
                self._current_window = NoPhotosPage(self._frame)
            elif self._current_window is None:
                self._current_window = NoPhotosPage(self._frame)
            else:
                raise TypeError()
            self._title_bar.set_button_enables(open_selection_mode=False)
        else:
            #self._page_number.append(0)
            #self._directory_info.append(CurrentDirectoryInfo(None, None))
            start_item = self._file_explorer.start_explorer()
            self._page_name = [start_item.title]
            new_page_id = start_item.new_page_id

            self._selection_mode = False

            if not isinstance(self._current_window, PhotoGalleryPage):
                if self._gallery_loading_windows:
                    self._current_window = self._gallery_loading_windows.pop()
                    self._current_window.selections_enabled = False
                else:
                    self._current_window = self._generate_new_gallery_page()
            self._current_window.setup_new_page(new_page_id)

            self._title_bar.title = os.path.join(*self._page_name)
            self._update_view()
            self._title_bar.set_button_enables(open_selection_mode=True)
        self._current_window.place(x=0, y=TITLE_BAR_HEIGHT, width=WINDOW_WIDTH, height=(WINDOW_HEIGHT - TITLE_BAR_HEIGHT*2), anchor="nw")

        super().place(**place_kwargs)

    def place_forget(self):
        # TODO: If selection mode, cancel selection changes?
        if self._update_view_job is not None:
            self._frame.after_cancel(self._update_view_job)
            self._update_view_job = None
            self._file_explorer.close_explorer()
        super().place_forget()

    def _generate_new_gallery_page(self):
        return PhotoGalleryPage(self._frame, self._open_item, self._select_item, self._unselect_item, self._selection_mode)

    def _generate_new_display_page(self):
        return PhotoDisplayPage(self._frame, self._select_item, self._unselect_item, self._selection_mode)

    def _update_view(self):
        update = self._file_explorer.get_view_update()
        if update is not None:
            if not isinstance(update, ViewUpdate):
                raise TypeError()
            if isinstance(update, (NameViewUpdate, SelectViewUpdate, FullImageViewUpdate)):
                self._current_window.update(update)
            elif isinstance(update, DirectionsUpdate):
                if update.selection == container.PhotoDirectorySelection.Not:
                    update_selection = elements.CheckBoxSelection.Unselected
                elif update.selection == container.PhotoDirectorySelection.Partial:
                    update_selection = elements.CheckBoxSelection.PartialSelect
                elif update.selection == container.PhotoDirectorySelection.All:
                    update_selection = elements.CheckBoxSelection.Selected
                elif update.selection is None:
                    update_selection = None
                else:
                    raise TypeError()
                self._title_bar.set_button_enables(
                    back=update.backwards,
                    forward=update.forwards,
                    up=update.up,
                    select_all=update_selection
                )
            else:
                raise TypeError()
        self._update_view_job = self._frame.after(200, self._update_view)

    def _goto_page(self, direction : PageDirection | int, current_page_id : Optional[int] = None):
        """This can be used for next, previous, up, or into

        direction is integer for into index
        """
        if current_page_id is None:
            if isinstance(self._current_window, (PhotoGalleryPage, PhotoDisplayPage)):
                current_page_id = self._current_window.page_id
            else:
                return

        if isinstance(direction, int):
            # If going into item, need to disable direction buttons until ready
            self._title_bar.set_button_enables(back=False, up=False, forward=False)
            self._file_explorer.request_go_into_page(current_page_id, direction)
        elif isinstance(direction, PageDirection):
            self._file_explorer.request_goto_page(current_page_id, direction)
        else:
            raise TypeError()

        if self._update_view_job is not None:
            self._frame.after_cancel(self._update_view_job)
            self._update_view_job = None

        new_page_info = self._file_explorer.get_page()
        if new_page_info.directory:
            if self._gallery_loading_windows:
                new_window = self._gallery_loading_windows.pop()
                new_window.selections_enabled = self._selection_mode
            else:
                new_window = self._generate_new_gallery_page()
        else:
            if self._display_loading_windows:
                new_window = self._display_loading_windows.pop()
                new_window.selections_enabled = self._selection_mode
            else:
                new_window = self._generate_new_display_page()

        if direction in (PageDirection.Previous, PageDirection.Next):
            pass
        elif direction == PageDirection.Up:
            self._page_name.pop()
            self._title_bar.title = os.path.join(*self._page_name)
            #if new_page_info.title is not None:
        elif isinstance(direction, int): # For into
            if new_page_info.title is None:
                raise Exception()
            self._page_name.append(new_page_info.title)
            self._title_bar.title = os.path.join(*self._page_name)

        new_window.setup_new_page(new_page_info.new_page_id)

        if isinstance(self._current_window, PhotoGalleryPage):
            self._gallery_loading_windows.append(self._current_window)
        elif isinstance(self._current_window, PhotoDisplayPage):
            self._display_loading_windows.append(self._current_window)

        old_window = self._current_window
        self._current_window = new_window
        self._current_window.place(x=0, y=TITLE_BAR_HEIGHT, width=WINDOW_WIDTH, height=(WINDOW_HEIGHT - TITLE_BAR_HEIGHT*2), anchor="nw")
        old_window.place_forget()

        self._update_view()

    def _goto_previous_page(self):
        self._goto_page(PageDirection.Previous)

    def _goto_next_page(self):
        self._goto_page(PageDirection.Next)

    def _goto_up_page(self):
        self._goto_page(PageDirection.Up)

    def _open_item(self, current_page_id, index):
        self._goto_page(index, current_page_id=current_page_id)

    def _start_selection_mode(self):
        if self._selection_mode:
            return
        self._selection_mode = True
        self._current_window.selections_enabled = self._selection_mode

    def _end_selection_mode(self, save=False):
        if not self._selection_mode:
            return
        self._selection_mode = False
        self._current_window.selections_enabled = self._selection_mode
        self._file_explorer.save_or_cancel_changes(save)
        if save:
            self._regenerate_slideshow()

    def _select_item(self, current_page_id, index):
        if not self._selection_mode:
            return
        self._file_explorer.request_selection(current_page_id, index, True)

    def _unselect_item(self, current_page_id, index):
        if not self._selection_mode:
            return
        self._file_explorer.request_selection(current_page_id, index, False)

    def _select_all_photos(self):
        if not self._selection_mode:
            return
        if isinstance(self._current_window, (PhotoGalleryPage, PhotoDisplayPage)):
            self._file_explorer.request_select_all(self._current_window.page_id, True)
            self._current_window.set_select_all(True)

    def _select_no_photos(self):
        if not self._selection_mode:
            return
        if isinstance(self._current_window, (PhotoGalleryPage, PhotoDisplayPage)):
            self._file_explorer.request_select_all(self._current_window.page_id, False)
            self._current_window.set_select_all(False)
