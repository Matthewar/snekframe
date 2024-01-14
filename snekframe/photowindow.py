"""Main window displaying photos"""

from collections import deque
import datetime
from enum import Enum, auto
import logging
import os.path
import time

import sqlalchemy
from sqlalchemy.sql.expression import func, select
import tkinter as tk
from tkinter import ttk

import PIL.Image
import PIL.ImageTk

from .analyse import load_photo_files, setup_viewed_photos
from . import elements
from . import icons
from .params import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    TITLE_BAR_HEIGHT,
    FILES_LOCATION,
    PHOTOS_LOCATION,
)
from .db import (
    SharedBase,
    RUNTIME_ENGINE,
    RUNTIME_SESSION,
    PERSISTENT_SESSION,
    CurrentDisplay,
    PhotoList,
)
from .fonts import FONTS
from .settings import SettingsWindow, SettingsContainer


class PhotoTitleBar:
    """Titlebar"""

    # class Mode(Enum):
    #    Settings = auto()
    #    PhotosVisible = auto() # Rename to gallery?
    #    PhotosHidden = auto()
    #    Selection = auto()

    def __init__(self, parent, open_selection, open_settings):
        self._frame = ttk.Frame(master=parent, style="TitleBar.TFrame")

        self._title = elements.UpdateLabel(
            self._frame, justify=tk.CENTER, font=FONTS.title, style="TitleBar"
        )
        self._title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._datetime = elements.AutoUpdateDateLabel(
            self._frame, justify=tk.RIGHT, font=FONTS.bold, style="TitleBar"
        )
        self._datetime.place(x=WINDOW_WIDTH - 15, rely=0.5, anchor="e")

        title_menu = ttk.Frame(master=self._frame, style="TitleBar.TFrame")
        title_menu.place(x=2.5, rely=0.5, anchor="w")
        self._title_menu_buttons = elements.RadioButtonSet(
            default_button_cls=elements.IconRadioButton, style="Title"
        )

        def callback_open_settings():
            open_settings()
            self._title.text = "Settings"

        self._settings_button = self._title_menu_buttons.add_button(
            title_menu, callback_open_settings, icon_name="settings", selected=False
        )
        self._settings_button.grid(row=0, column=0, padx=(15, 5))

        def callback_open_selection():
            open_selection()
            self._title.text = "Select Photos"

        self._select_button = self._title_menu_buttons.add_button(
            title_menu, callback_open_selection, icon_name="slideshow", selected=False
        )
        self._select_button.grid(row=0, column=1, padx=5)

        self._visible = False

    @property
    def visible(self):
        """If the title bar is visible"""
        return self._visible

    def place(self, unpause_datetime=True):
        self._frame.place(
            x=0, y=0, anchor="nw", width=WINDOW_WIDTH, height=TITLE_BAR_HEIGHT
        )
        self._frame.tkraise()
        if unpause_datetime:
            self._datetime.update_label()
        self._visible = True

    def place_forget(self, pause_datetime=True):
        self._frame.place_forget()
        if pause_datetime:
            self._datetime.pause_updates()
        self._visible = False

    def display_photo_title(self, title):
        self._title.text = title
        self._title_menu_buttons.deselect_all()

    def invoke_settings_button(self):
        """Invoke the settings button

        This will trigger updating this class for settings along with the settings callback triggers
        """
        self._settings_button.invoke()

    def invoke_selection_button(self):
        """Invoke the photo selection button

        This will trigger updating this class for selection along with the selection callback triggers
        """
        self._select_button.invoke()


class PhotoSelectionWindow:
    """Allows user to select which photos to display"""

    def __init__(self, frame, select_album_callback):
        self._main_window = frame
        self._inner_window = None
        self._select_album_callback = select_album_callback

        self._generate_window()

    BUTTON_HEIGHT = 150
    BUTTON_VERTICAL_PADDING = 25
    BUTTON_WIDTH = 300

    def place(self, **place_args):
        if self._inner_window is None:
            self._generate_window()
        self._main_window.place(**place_args)

    def place_forget(self):
        self._main_window.place_forget()

    def _generate_window(self):  # TODO: Add regeneration after rescan (if changes)
        if self._inner_window is not None:
            self._inner_window.destroy()
            self._innner_window = None

        with PERSISTENT_SESSION() as session:
            albums = session.scalars(select(PhotoList.album).distinct()).all()

            num_albums = len(albums)

        if num_albums == 0:
            self._inner_window = ttk.Frame(
                self._main_window,
                width=WINDOW_WIDTH,
                height=WINDOW_HEIGHT - TITLE_BAR_HEIGHT,
            )
            main_label = ttk.Label(
                self._inner_window, text="No Photos Available", font=FONTS.title
            )
            subtitle_label = ttk.Label(
                self._inner_window,
                text="Go to settings to scan for photos",
                font=FONTS.subtitle,
            )

            elements = (main_label, subtitle_label)

            # TODO: Function for this?

            for row, element in enumerate(elements, start=1):
                element.grid(row=row, column=1)

            self._inner_window.grid_columnconfigure(0, weight=1)
            self._inner_window.grid_columnconfigure(2, weight=1)
            self._inner_window.grid_rowconfigure(0, weight=1)
            self._inner_window.grid_rowconfigure(len(elements) + 1, weight=1)

            self._inner_window.place(
                x=0,
                y=0,
                anchor="nw",
                width=WINDOW_WIDTH,
                height=WINDOW_HEIGHT - TITLE_BAR_HEIGHT,
            )
        else:
            num_rows = num_albums // 3 + 1
            inner_window_height = (
                self.BUTTON_HEIGHT + self.BUTTON_VERTICAL_PADDING * 2
            ) * (num_rows + 1)
            self._inner_window = ttk.Frame(
                self._main_window, width=WINDOW_WIDTH, height=inner_window_height
            )

            all_photos_button = ttk.Button(
                self._inner_window,
                text="All Photos",
                command=lambda: self._select_album_callback(all_photos=True),
            )
            all_photos_button.grid(
                row=0, column=1, columnspan=3, pady=self.BUTTON_VERTICAL_PADDING
            )

            all_items = [self._inner_window, all_photos_button]

            current_row = 1
            current_column = 1
            get_select_album = lambda album: (
                lambda: self._select_album_callback(album=album)
            )
            for album in albums:
                album_button = ttk.Button(
                    self._inner_window, text=album, command=get_select_album(album)
                )
                album_button.grid(
                    row=current_row,
                    column=current_column,
                    pady=self.BUTTON_VERTICAL_PADDING,
                    padx=10,
                )  # BUTTON_HORIZONTAL_PADDING

                if current_column == 3:
                    current_row += 1
                    current_column = 1
                else:
                    current_column += 1

                all_items.append(album_button)

            self._inner_window.grid_columnconfigure(0, weight=1)
            self._inner_window.grid_columnconfigure(4, weight=1)
            self._inner_window.grid_rowconfigure(current_row + 1, weight=1)

            self._inner_window.place(x=0, y=0, anchor="nw", width=WINDOW_WIDTH)

            # TODO: Add vertical scroll


class PhotoDisplayWindow:
    _NUM_PHOTOS_LOADED = 3

    # TODO: Keep title open if clicking on it

    def __init__(self, frame, settings, show_title, hide_title):
        self._window = frame  # Visible frame
        self._settings = settings
        self._show_title = show_title
        self._hide_title = hide_title

        self._inner_window = ttk.Frame(
            master=self._window,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            style="DisplayWindow.TFrame",
        )  # TODO: Unnecessary layer?
        self._photo = None
        self._image_left = None
        self._image_centre = None
        self._image_right = None

        self._image_ids = deque([None] * 5, maxlen=5)

        self._pause_transitions = True
        self._last_action_time = datetime.datetime.now()
        self._last_transition_time = datetime.datetime.now()
        self._action = None
        self._action_job = None
        self._action_timer = None
        self._inner_window.after(10000, self._transition_next_photo)

        self._remove_title_job = None

        self._title_showing = False

        self.regenerate_window()

    def place(self, **place_kwargs):
        self._pause_transitions = False
        self._last_action_time = datetime.datetime.now()
        self._last_transition_time = datetime.datetime.now()
        self._title_showing = False
        self._window.place(**place_kwargs)

    def place_forget(self):
        self._pause_transitions = True
        self._title_showing = False
        self._window.place_forget()

    @staticmethod
    def _get_resized_image_dimensions(image):
        scale_x = WINDOW_WIDTH / image.width
        scale_y = WINDOW_HEIGHT / image.height

        if scale_x < scale_y:
            return image.width * scale_x, image.height * scale_y
        return image.width * scale_y, image.height * scale_y

    @classmethod
    def _resize_image(cls, image):
        PIL.ImageOps.exif_transpose(image, in_place=True)
        x, y = cls._get_resized_image_dimensions(image)
        return image.resize((int(x), int(y)), PIL.Image.LANCZOS)

    def regenerate_window(self):
        # Can just rearrange
        if self._photo is not None:
            self._photo.destroy()

        self._pause_transitions = True
        self._last_action_time = datetime.datetime.now()
        self._last_transition_time = datetime.datetime.now()
        self._inner_window.after(10000, self._transition_next_photo)

        self._title_showing = False

        self._photo = ttk.Label(
            self._inner_window,
            text="There should be a photo here",
            style="Image.DisplayWindow.TLabel",
        )
        self._photo.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self._inner_window.place(x=0, y=0, anchor="nw")

        self._image_ids.clear()
        photos = {}

        self._image_ids.append(None)
        with RUNTIME_SESSION() as session:
            # For now just looking forwards?
            for row in session.scalars(select(PhotoList).limit(4)):
                self._image_ids.append(row.id)
                photos[row.id] = os.path.join(
                    FILES_LOCATION, PHOTOS_LOCATION, row.album, row.filename
                )
        if len(self._image_ids) == 2:
            self._image_ids.extend([self._image_ids[1]] * 2 + [None])
        elif len(self._image_ids) == 3:
            self._image_ids.extend([self._image_ids[1], self._image_ids[2]])
        elif len(self._image_ids) == 4:
            self._image_ids.append(None)

        self._image_left = PIL.ImageTk.PhotoImage(
            self._resize_image(PIL.Image.open(photos[self._image_ids[1]]))
        )
        self._image_centre = PIL.ImageTk.PhotoImage(
            self._resize_image(PIL.Image.open(photos[self._image_ids[2]]))
        )
        self._photo.configure(image=self._image_centre)
        self._photo.image = self._image_centre
        self._image_right = PIL.ImageTk.PhotoImage(
            self._resize_image(PIL.Image.open(photos[self._image_ids[3]]))
        )

        self._inner_window.bind("<Button-1>", self._frame_detect_click)
        self._inner_window.bind("<ButtonRelease-1>", self._frame_detect_release)
        self._photo.bind("<Button-1>", self._photo_detect_click)
        self._photo.bind("<ButtonRelease-1>", self._photo_detect_release)

    def _frame_detect_click(self, event):
        if len(self._image_ids) == 1:
            return self._menu_click(event)

        if event.x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_click(event)
        elif event.x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_click(event)
        else:
            return self._menu_click(event)

    def _frame_detect_release(self, event):
        if len(self._image_ids) == 1:
            return self._menu_release(event)

        if event.x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_release(event)
        elif event.x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_release(event)
        else:
            return self._menu_release(event)

    def _photo_detect_click(self, event):
        if len(self._image_ids) == 1:
            return self._menu_click(event)

        x = event.x - (self._photo.winfo_reqwidth() / 2) + (WINDOW_WIDTH / 2)

        if x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_click(event)
        elif x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_click(event)
        else:
            return self._menu_click(event)

    def _photo_detect_release(self, event):
        if len(self._image_ids) == 1:
            return self._menu_release(event)

        x = event.x - (self._photo.winfo_reqwidth() / 2) + (WINDOW_WIDTH / 2)

        if x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_release(event)
        elif x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_release(event)
        else:
            return self._menu_release(event)

    def _get_forward_image(self):
        forward_query = select(PhotoList)
        if self._image_ids[4] is not None:
            forward_query = forward_query.where(PhotoList.id >= self._image_ids[4])
        forward_query = forward_query.order_by(PhotoList.id).limit(2)

        with RUNTIME_SESSION() as session:
            forward_images = session.scalars(forward_query).all()
            next_image = forward_images[0]
            self._image_ids.append(next_image.id)
            if len(forward_images) > 1:
                self._image_ids.append(forward_images[1].id)
            else:
                self._image_ids.append(None)

        return next_image

    def _get_reverse_image(self):
        reverse_query = select(PhotoList)
        if self._image_ids[0] is not None:
            reverse_query = reverse_query.where(PhotoList.id <= self._image_ids[0])
        reverse_query = reverse_query.order_by(PhotoList.id.desc()).limit(2)

        with RUNTIME_SESSION() as session:
            reverse_images = session.scalars(reverse_query).all()
            prev_image = reverse_images[0]
            self._image_ids.appendleft(prev_image.id)
            if len(reverse_images) > 1:
                self._image_ids.appendleft(reverse_images[1].id)
            else:
                self._image_ids.appendleft(None)

        return prev_image

    class _ActionType(Enum):
        Reverse = auto()
        Forward = auto()
        Menu = auto()

    def _reverse_image_click(self, event):
        if self._action_job is not None:
            self._inner_window.after_cancel(self._action_job)
            self._action_job = None
        self._pause_transitions = True

        if self._action is None:
            self._action_timer = time.time_ns()
            self._action = self._ActionType.Reverse
            self._action_job = self._inner_window.after(500, self._try_complete_action)
        elif self._action == self._ActionType.Reverse:
            if (time.time_ns() - self._action_timer) <= 500000000:
                self._switch_reverse_image()
            self._action_timer = None
            self._action = None
        else:
            self._action = None
            self._action_timer = None

        self._last_action_time = datetime.datetime.now()

    def _reverse_image_release(self, event):
        self._pause_transitions = False
        self._last_action_time = datetime.datetime.now()

    def _forward_image_click(self, event):
        if self._action_job is not None:
            self._inner_window.after_cancel(self._action_job)
            self._action_job = None
        self._pause_transitions = True

        if self._action is None:
            self._action_timer = time.time_ns()
            self._action = self._ActionType.Forward
            self._action_job = self._inner_window.after(500, self._try_complete_action)
        elif self._action == self._ActionType.Forward:
            if (time.time_ns() - self._action_timer) <= 500000000:
                self._switch_forward_image()
            self._action_timer = None
            self._action = None
        else:
            self._action = None
            self._action_timer = None

        self._last_action_time = datetime.datetime.now()

    def _forward_image_release(self, event):
        self._pause_transitions = False
        self._last_action_time = datetime.datetime.now()

    def _menu_click(self, event):
        if self._action_job is not None:
            self._inner_window.after_cancel(self._action_job)
            self._action_job = None
        self._pause_transitions = True

        if self._action is None:
            self._action_timer = time.time_ns()
            self._action = self._ActionType.Menu
            self._action_job = self._inner_window.after(500, self._try_complete_action)
        else:
            self._action = None
            self._action_timer = None

        self._last_action_time = datetime.datetime.now()

    def _menu_release(self, event):
        self._pause_transitions = False
        self._last_action_time = datetime.datetime.now()

    def _try_complete_action(self):
        if self._action is None:
            return
        if self._title_showing:
            self._hide_title()
            self._title_showing = False
            if self._remove_title_job is not None:
                self._inner_window.after_cancel(self._remove_title_job)
                self._remove_title_job = None
        else:
            self._show_title()
            self._title_showing = True
            self._remove_title_job = self._inner_window.after(
                3000, self._check_remove_title
            )

        self._action_timer = None
        self._action = None
        self._action_job = None

    def _switch_forward_image(self):
        self._photo.configure(image=self._image_right)
        self._photo.image = self._image_right

        self._image_left = self._image_centre
        self._image_centre = self._image_right

        new_image_right_info = self._get_forward_image()
        self._image_right = PIL.ImageTk.PhotoImage(
            self._resize_image(
                PIL.Image.open(
                    os.path.join(
                        FILES_LOCATION,
                        PHOTOS_LOCATION,
                        new_image_right_info.album,
                        new_image_right_info.filename,
                    )
                )
            )
        )

    def _switch_reverse_image(self):
        self._photo.configure(image=self._image_left)
        self._photo.image = self._image_left

        self._image_right = self._image_centre
        self._image_centre = self._image_left

        new_image_left_info = self._get_reverse_image()
        self._image_left = PIL.ImageTk.PhotoImage(
            self._resize_image(
                PIL.Image.open(
                    os.path.join(
                        FILES_LOCATION,
                        PHOTOS_LOCATION,
                        new_image_left_info.album,
                        new_image_left_info.filename,
                    )
                )
            )
        )

    def _transition_next_photo(self):
        if not self._pause_transitions:
            current_time = datetime.datetime.now()

            timedelta = current_time - self._last_transition_time
            if timedelta < self._settings.photo_change_time:
                trigger_after_secs = self._settings.photo_change_time - timedelta
                self._inner_window.after(
                    int(trigger_after_secs.total_seconds() * 1000),
                    self._transition_next_photo,
                )
                return

            timedelta = current_time - self._last_action_time
            if timedelta < datetime.timedelta(seconds=10):
                seconds_since_event = timedelta.total_seconds()
                if seconds_since_event < 9.0:
                    self._inner_window.after(
                        int((10 - seconds_since_event) * 1000),
                        self._transition_next_photo,
                    )
                    return

            self._photo.configure(image=self._image_right)
            self._photo.image = self._image_right
            self._image_left = self._image_centre
            self._image_centre = self._image_right

            image_right_info = self._get_forward_image()
            self._image_right = PIL.ImageTk.PhotoImage(
                self._resize_image(
                    PIL.Image.open(
                        os.path.join(
                            FILES_LOCATION,
                            PHOTOS_LOCATION,
                            image_right_info.album,
                            image_right_info.filename,
                        )
                    )
                )
            )
            self._last_transition_time = datetime.datetime.now()

        self._inner_window.after(10000, self._transition_next_photo)

    def _check_remove_title(self):
        self._remove_title_job = None
        if not self._title_showing:
            return
        timedelta = datetime.datetime.now() - self._last_action_time
        if timedelta >= datetime.timedelta(seconds=3):
            self._hide_title()
            self._title_showing = False
        else:
            self._remove_title_job = self._inner_window.after(
                int(timedelta.total_seconds() * 1000), self._check_remove_title
            )


class PhotoWindow:
    """Photo window is made of 3 photos so they don't have to be loaded while the photos are dragged"""

    class SelectedPhotos:
        def __init__(self, album=None, all_photos=False):
            if album is not None and all_photos:
                raise Exception("Can't have both album selected and all photos")
            if album is not None and not isinstance(album, str):
                raise TypeError("album must be a string or None")
            if not isinstance(all_photos, bool):
                raise TypeError("all_photos must be a boolean")
            self._album = album
            self._all_photos = all_photos

        def set_album(self, album):
            if not isinstance(album, str):
                raise TypeError("album must be a string")
            self._album = album
            self._all_photos = False

        def set_all_photos(self):
            self._album = None
            self._all_photos = True

        def set_no_selection(self):
            self._album = None
            self._all_photos = False

        @property
        def photos_selected(self):
            return self._album is not None or self._all_photos

        @property
        def album_selected(self):
            return self._album is not None

        @property
        def album(self):
            if self.album_selected:
                return self._album
            raise AttributeError("album is not selected")

        @property
        def all_photos_selected(self):
            return self._all_photos

        def __eq__(self, other):
            if not isinstance(other, PhotoWindow.SelectedPhotos):
                return False
            return self._album == other._album and self._all_photos == other._all_photos

        def update(self, other):
            if not isinstance(other, PhotoWindow.SelectedPhotos):
                raise TypeError("other must be same type")
            self._album = other._album
            self._all_photos = other._all_photos

        def __repr__(self):
            if self.all_photos_selected:
                return "SelectedPhotos(all_photos_selected)"
            if self.album_selected:
                return f"SelectedPhotos(album={self.album})"
            return "SelectedPhotos(no_photos_selected)"

    class OpenWindow(Enum):
        Select = auto()
        Display = auto()
        Settings = auto()

    def __init__(self, frame):
        self._window = frame

        SharedBase.metadata.create_all(RUNTIME_ENGINE)

        load_photo_files()

        self._selection = self.SelectedPhotos()
        self._settings = SettingsContainer()

        with PERSISTENT_SESSION() as persistent_session:
            display_info_result = persistent_session.scalars(
                select(CurrentDisplay).limit(1)
            )
            display_info_row = (
                display_info_result.one_or_none()
            )  # throws MultipleResultsFound if multiple rows somehow found TODO
            if display_info_row is not None:
                self._selection = self.SelectedPhotos(
                    album=display_info_row.album, all_photos=display_info_row.all_photos
                )

            if self._selection.photos_selected:
                found_photos = self._setup_viewed_photos()

                if not found_photos:
                    self._selection.set_no_selection()

        self._title_bar = PhotoTitleBar(
            self._window, self._open_photo_select_window, self._open_settings
        )
        self._selection_window = None
        self._display_window = None
        self._settings_window = None

        self._current_window = None

        if not self._selection.photos_selected:
            self._title_bar.invoke_selection_button()
        else:
            self._open_photo_display_window()

    def place(self, **place_kwargs):
        self._window.place(**place_kwargs)

    def _close_current_window(self):
        if self._current_window is None:
            return  # Skip, should only occur on startup
        if self._current_window == self.OpenWindow.Select:
            assert self._selection_window is not None
            self._selection_window.place_forget()
        elif self._current_window == self.OpenWindow.Display:
            assert self._display_window is not None
            self._display_window.place_forget()
        elif self._current_window == self.OpenWindow.Settings:
            assert self._settings_window is not None
            self._settings_window.place_forget()
        else:
            raise TypeError()

        self._current_window = None

    def _open_photo_select_window(self):
        if not self._title_bar.visible:
            self._title_bar.place()
        self._close_current_window()

        if self._selection_window is None:
            self._selection_window = PhotoSelectionWindow(
                ttk.Frame(
                    master=self._window,
                    width=WINDOW_WIDTH,
                    height=WINDOW_HEIGHT - TITLE_BAR_HEIGHT,
                ),
                self._callback_open_photo_display_window,
            )
        self._selection_window.place(x=0, y=TITLE_BAR_HEIGHT, anchor="nw")
        self._current_window = self.OpenWindow.Select

    def _callback_open_photo_display_window(self, album=None, all_photos=False):
        new_selection = self.SelectedPhotos(album=album, all_photos=all_photos)

        if new_selection != self._selection:
            self._selection.update(new_selection)
            self._setup_viewed_photos()  # If returns false there were no photos somehow
            regenerate = True
        else:
            regenerate = False
        return self._open_photo_display_window(regenerate=regenerate)

    def _setup_viewed_photos(self):
        if self._selection.album_selected:
            album = self._selection.album
        else:
            album = None

        return setup_viewed_photos(shuffle=self._settings.shuffle_photos, album=album)

    def _open_photo_display_window(self, regenerate=False):
        # TODO: Regenerate if settings change (rescan done)
        if self._title_bar.visible:
            self._title_bar.place_forget()
        self._close_current_window()

        if self._display_window is None:
            self._display_window = PhotoDisplayWindow(
                ttk.Frame(
                    master=self._window, width=WINDOW_WIDTH, height=WINDOW_HEIGHT
                ),
                self._settings,
                self._title_bar.place,
                self._title_bar.place_forget,
            )
        elif regenerate:
            self._display_window.regenerate_window()

        if self._selection.all_photos_selected:
            self._title_bar.display_photo_title("All Photos")
        else:
            self._title_bar.display_photo_title(self._selection.album)

        self._display_window.place(x=0, y=0, anchor="nw")
        self._current_window = self.OpenWindow.Display

    def _destroy_photo_window(self, display_window=True, selection_window=True):
        if self._display_window is not None and display_window:
            self._display_window.place_forget()
            del self._display_window
            self._display_window = None
        if self._selection_window is not None and selection_window:
            self._selection_window.place_forget()
            del self._selection_window
            self._selection_window = None

    def _open_settings(self):
        if not self._title_bar.visible:
            self._title_bar.place()
        self._close_current_window()

        if self._settings_window is None:
            # TODO: Need to be able to exit to previous window from here
            self._settings_window = SettingsWindow(
                self._window,
                self._selection,
                self._settings,
                self._destroy_photo_window,
            )
        self._settings_window.place(
            x=0,
            y=TITLE_BAR_HEIGHT,
            anchor="nw",
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT - TITLE_BAR_HEIGHT,
        )
        self._current_window = self.OpenWindow.Settings
