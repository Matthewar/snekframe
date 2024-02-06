"""Photo Display Window"""

from collections import deque
from dataclasses import dataclass
import datetime
from enum import Enum, auto
import os.path
import time
from typing import Callable, Iterable

import tkinter as tk
from tkinter import ttk

from sqlalchemy.sql.expression import select

from PIL import Image as PIL_Image, ImageTk as PIL_ImageTk, ImageOps as PIL_ImageOps

from .. import elements, settings
from ..db import RUNTIME_SESSION, PERSISTENT_SESSION, PhotoListV1
from ..db.runtime import PhotoOrder
from ..params import WINDOW_HEIGHT, WINDOW_WIDTH, FILES_LOCATION, PHOTOS_LOCATION

def _get_resized_image_dimensions(image, max_width=WINDOW_WIDTH, max_height=WINDOW_HEIGHT):
    scale_x = max_width / image.width
    scale_y = max_height / image.height

    if scale_x < scale_y:
        return image.width * scale_x, image.height * scale_y
    return image.width * scale_y, image.height * scale_y

def _resize_image(image, max_width=WINDOW_WIDTH, max_height=WINDOW_HEIGHT):
    PIL_ImageOps.exif_transpose(image, in_place=True)
    size_x, size_y = _get_resized_image_dimensions(image, max_width=max_width, max_height=max_height)
    return image.resize((int(size_x), int(size_y)), PIL_Image.LANCZOS)

@dataclass
class _ImageIdPair:
    ordering_id : int
    photo_id : int

class PhotoDisplayWindow(elements.LimitedFrameBaseElement):
    _NUM_PHOTOS_LOADED = 3

    # TODO: Keep title open if clicking on it

    def __init__(
            self,
            parent : tk.Frame,
            settings_container : settings.SettingsContainer,
            show_title : Callable[[], None],
            hide_title : Callable[[], None]):
        super().__init__(parent, {}, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, style="DisplayWindow")

        self._settings = settings_container
        self._show_title = show_title
        self._hide_title = hide_title

        self._photo = None
        self._image_left = None
        self._image_centre = None
        self._image_right = None

        self._image_ids = deque([None] * 5, maxlen=5)

        self._photo_change_job = None
        self._last_action_time = datetime.datetime.now()
        self._last_transition_time = datetime.datetime.now()
        self._action = None
        self._action_job = None
        self._action_timer = None

        self._remove_title_job = None

        self._title_showing = False

        self.regenerate_window()

    def place(self, **place_kwargs):
        self._photo_change_job = self._frame.after(10000, self._transition_next_photo)
        self._last_action_time = datetime.datetime.now()
        self._last_transition_time = datetime.datetime.now()
        self._title_showing = False
        super().place(**place_kwargs)

    def place_forget(self):
        if self._photo_change_job is not None:
            self._frame.after_cancel(self._photo_change_job)
            self._photo_change_job = None
        self._title_showing = False
        super().place_forget()

    def regenerate_window(self):
        # Can just rearrange
        if self._photo is not None:
            self._photo.destroy()

        self._last_action_time = datetime.datetime.now()
        self._last_transition_time = datetime.datetime.now()

        self._title_showing = False

        self._photo = ttk.Label(self._frame, text="There should be a photo here", style="Image.DisplayWindow.TLabel")
        self._photo.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._image_ids.clear()

        self._image_ids.append(None)
        with RUNTIME_SESSION() as session:
            # For now just looking forwards?
            for row in session.scalars(select(PhotoOrder).limit(4)):
                self._image_ids.append(_ImageIdPair(ordering_id=row.id, photo_id=row.photo_id))
        if len(self._image_ids) == 2:
            self._image_ids.extend([self._image_ids[1]]*2 + [None])
        elif len(self._image_ids) == 3:
            self._image_ids.extend([self._image_ids[1], self._image_ids[2]])
        elif len(self._image_ids) == 4:
            self._image_ids.append(None)

        self._image_left = PIL_ImageTk.PhotoImage(
            _resize_image(
                PIL_Image.open(
                    self._get_photo_paths(self._image_ids[1].photo_id)[0]
                )
            )
        )
        self._image_centre = PIL_ImageTk.PhotoImage(
            _resize_image(
                PIL_Image.open(
                    self._get_photo_paths(self._image_ids[2].photo_id)[0]
                )
            )
        )
        self._photo.configure(image=self._image_centre)
        self._photo.image = self._image_centre
        self._image_right = PIL_ImageTk.PhotoImage(
            _resize_image(
                PIL_Image.open(
                    self._get_photo_paths(self._image_ids[3].photo_id)[0]
                )
            )
        )

        self._frame.bind("<Button-1>", self._frame_detect_click)
        self._frame.bind("<ButtonRelease-1>", self._frame_detect_release)
        self._photo.bind("<Button-1>", self._photo_detect_click)
        self._photo.bind("<ButtonRelease-1>", self._photo_detect_release)

        self._photo_change_job = self._frame.after(10000, self._transition_next_photo)

    def _get_photo_paths(self, *ids : _ImageIdPair):
        results = []
        with PERSISTENT_SESSION() as session:
            for id_set in ids:
                result = session.execute(
                    select(PhotoListV1.filename, PhotoListV1.path).where(PhotoListV1.id == id_set.photo_id)
                ).one()
                results.append(os.path.join(FILES_LOCATION, PHOTOS_LOCATION, result[1], result[0]))
        return results


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
        forward_query = select(PhotoOrder)
        if self._image_ids[4] is not None:
            forward_query = forward_query.where(PhotoOrder.id >= self._image_ids[4].ordering_id)
        forward_query = forward_query.order_by(PhotoOrder.id).limit(2)

        with RUNTIME_SESSION() as session:
            forward_images = session.scalars(forward_query).all()
            next_image = forward_images[0]
            self._image_ids.append(_ImageIdPair(ordering_id=next_image.id, photo_id=next_image.photo_id))
            if len(forward_images) > 1:
                self._image_ids.append(_ImageIdPair(ordering_id=forward_images[1].id, photo_id=forward_images[1].photo_id))
            else:
                self._image_ids.append(None)

        return next_image

    def _get_reverse_image(self):
        reverse_query = select(PhotoOrder)
        if self._image_ids[0] is not None:
            reverse_query = reverse_query.where(PhotoOrder.id <= self._image_ids[0].ordering_id)
        reverse_query = reverse_query.order_by(PhotoOrder.id.desc()).limit(2)

        with RUNTIME_SESSION() as session:
            reverse_images = session.scalars(reverse_query).all()
            prev_image = reverse_images[0]
            self._image_ids.appendleft(_ImageIdPair(ordering_id=prev_image.id, photo_id=prev_image.photo_id))
            if len(reverse_images) > 1:
                self._image_ids.appendleft(_ImageIdPair(ordering_id=reverse_images[1].id, photo_id=reverse_images[1].photo_id))
            else:
                self._image_ids.appendleft(None)

        return prev_image

    class _ActionType(Enum):
        Reverse = auto()
        Forward = auto()
        Menu = auto()

    def _reverse_image_click(self, event):
        if self._action_job is not None:
            self._frame.after_cancel(self._action_job)
            self._action_job = None

        if self._action is None:
            self._action_timer = time.time_ns()
            self._action = self._ActionType.Reverse
            self._action_job = self._frame.after(500, self._try_complete_action)
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
        self._last_action_time = datetime.datetime.now()

    def _forward_image_click(self, event):
        if self._action_job is not None:
            self._frame.after_cancel(self._action_job)
            self._action_job = None

        if self._action is None:
            self._action_timer = time.time_ns()
            self._action = self._ActionType.Forward
            self._action_job = self._frame.after(500, self._try_complete_action)
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
        self._last_action_time = datetime.datetime.now()

    def _menu_click(self, event):
        if self._action_job is not None:
            self._frame.after_cancel(self._action_job)
            self._action_job = None

        if self._action is None:
            self._action_timer = time.time_ns()
            self._action = self._ActionType.Menu
            self._action_job = self._frame.after(500, self._try_complete_action)
        else:
            self._action = None
            self._action_timer = None

        self._last_action_time = datetime.datetime.now()

    def _menu_release(self, event):
        self._last_action_time = datetime.datetime.now()

    def _try_complete_action(self):
        if self._action is None:
            return
        if self._title_showing:
            self._hide_title()
            self._title_showing = False
            if self._remove_title_job is not None:
                self._frame.after_cancel(self._remove_title_job)
                self._remove_title_job = None
        else:
            self._show_title()
            self._title_showing = True
            self._remove_title_job = self._frame.after(3000, self._check_remove_title)

        self._action_timer = None
        self._action = None
        self._action_job = None

    def _switch_forward_image(self):
        self._photo.configure(image=self._image_right)
        self._photo.image = self._image_right

        self._image_left = self._image_centre
        self._image_centre = self._image_right

        new_image_right_info = self._get_forward_image()
        self._image_right = PIL_ImageTk.PhotoImage(_resize_image(PIL_Image.open(os.path.join(FILES_LOCATION, PHOTOS_LOCATION, new_image_right_info.album, new_image_right_info.filename))))

    def _switch_reverse_image(self):
        self._photo.configure(image=self._image_left)
        self._photo.image = self._image_left

        self._image_right = self._image_centre
        self._image_centre = self._image_left

        new_image_left_info = self._get_reverse_image()
        self._image_left = PIL_ImageTk.PhotoImage(_resize_image(PIL_Image.open(os.path.join(FILES_LOCATION, PHOTOS_LOCATION, new_image_left_info.album, new_image_left_info.filename))))

    def _transition_next_photo(self):
        current_time = datetime.datetime.now()

        timedelta = current_time - self._last_transition_time
        if timedelta < self._settings.photo_change_time:
            trigger_after_secs = self._settings.photo_change_time - timedelta
            self._photo_change_job = self._frame.after(int(trigger_after_secs.total_seconds() * 1000), self._transition_next_photo)
            return

        timedelta = current_time - self._last_action_time
        if timedelta < datetime.timedelta(seconds=10):
            seconds_since_event = timedelta.total_seconds()
            if seconds_since_event < 9.0:
                self._photo_change_job = self._frame.after(int((10-seconds_since_event)*1000), self._transition_next_photo)
                return

        self._photo.configure(image=self._image_right)
        self._photo.image = self._image_right
        self._image_left = self._image_centre
        self._image_centre = self._image_right

        image_right_info = self._get_forward_image()
        self._image_right = PIL_ImageTk.PhotoImage(_resize_image(PIL_Image.open(os.path.join(FILES_LOCATION, PHOTOS_LOCATION, image_right_info.album, image_right_info.filename))))
        self._last_transition_time = datetime.datetime.now()

        self._photo_change_job = self._frame.after(10000, self._transition_next_photo)

    def _check_remove_title(self):
        # TODO: Need to capture menu events and prevent closing while in progress?
        self._remove_title_job = None
        if not self._title_showing:
            return
        timedelta = datetime.datetime.now() - self._last_action_time
        if timedelta >= datetime.timedelta(seconds=3):
            self._hide_title()
            self._title_showing = False
        else:
            self._remove_title_job = self._frame.after(int(timedelta.total_seconds()*1000), self._check_remove_title)
