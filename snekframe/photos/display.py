"""Photo Display Window"""

from collections import deque
from dataclasses import dataclass
import datetime
from enum import Enum, auto
import logging
import os.path
import time
from typing import Callable, Iterable

import tkinter as tk
from tkinter import ttk

from sqlalchemy.sql.expression import select, update

from PIL import Image as PIL_Image, ImageTk as PIL_ImageTk, ImageOps as PIL_ImageOps, UnidentifiedImageError

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
            hide_title : Callable[[], None],
            disable_slideshow : Callable[[], None]):
        super().__init__(parent, {}, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, style="DisplayWindow")

        self._settings = settings_container
        self._show_title = show_title
        self._hide_title = hide_title
        self._disable_slideshow = disable_slideshow

        self._photo = None

        self._image_ids : deque[_ImageIdPair] = deque(maxlen=3)
        self._loaded_images : deque[PIL_ImageTk.PhotoImage] = deque(maxlen=3)

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
        if len(self._loaded_images) > 1:
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

        self._photo = ttk.Label(self._frame, text="Error: Photos unable to load. Try rescan.", style="Image.DisplayWindow.TLabel")
        self._photo.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._image_ids.clear()
        self._loaded_images.clear()

        discovered_photos = 0
        loaded_all_photos = True
        last_image_ordering_id = None
        image_query = select(PhotoOrder).where(PhotoOrder.lost == False)

        with RUNTIME_SESSION() as session:
            while len(self._loaded_images) < 3:
                new_image_query = image_query if last_image_ordering_id is None else image_query.where(PhotoOrder.id > last_image_ordering_id)
                new_image_row = session.scalars(
                    new_image_query.limit(1)
                ).one_or_none()

                if new_image_row is None:
                    break

                last_image_ordering_id = new_image_row.id
                new_image_id = _ImageIdPair(ordering_id=new_image_row.id, photo_id=new_image_row.photo_id)
                photo_path = self._get_photo_paths(new_image_id)[0]
                try:
                    new_image = PIL_Image.open(photo_path)
                except FileNotFoundError:
                    logging.warning("Cannot find photo '%s'", photo_path)
                except UnidentifiedImageError:
                    logging.warning("Unable to open file '%s'", photo_path)
                else:
                    self._image_ids.append(new_image_id)
                    self._loaded_images.append(
                        PIL_ImageTk.PhotoImage(
                            _resize_image(
                                new_image
                            )
                        )
                    )
                    continue
                loaded_all_photos = False
                session.execute(
                    update(PhotoOrder).where(PhotoOrder.id == new_image_id.ordering_id).values(lost=True)
                )
            if not loaded_all_photos:
                session.commit()

        if len(self._loaded_images) > 0:
            if len(self._loaded_images) > 1:
                main_image = self._loaded_images[1]
            else:
                main_image = self._loaded_images[0]
            self._photo.configure(image=main_image)
            self._photo.image = main_image
        else:
            self._disable_slideshow()

        self._frame.bind("<Button-1>", self._frame_detect_click)
        self._frame.bind("<ButtonRelease-1>", self._frame_detect_release)
        self._photo.bind("<Button-1>", self._photo_detect_click)
        self._photo.bind("<ButtonRelease-1>", self._photo_detect_release)

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
        if len(self._image_ids) <= 1:
            return self._menu_click(event)

        if event.x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_click(event)
        elif event.x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_click(event)
        else:
            return self._menu_click(event)

    def _frame_detect_release(self, event):
        if len(self._image_ids) <= 1:
            return self._menu_release(event)

        if event.x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_release(event)
        elif event.x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_release(event)
        else:
            return self._menu_release(event)

    def _photo_detect_click(self, event):
        if len(self._image_ids) <= 1:
            return self._menu_click(event)

        x = event.x - (self._photo.winfo_reqwidth() / 2) + (WINDOW_WIDTH / 2)

        if x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_click(event)
        elif x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_click(event)
        else:
            return self._menu_click(event)

    def _photo_detect_release(self, event):
        if len(self._image_ids) <= 1:
            return self._menu_release(event)

        x = event.x - (self._photo.winfo_reqwidth() / 2) + (WINDOW_WIDTH / 2)

        if x < ((WINDOW_WIDTH / 2) - 50):
            return self._reverse_image_release(event)
        elif x > ((WINDOW_WIDTH / 2) + 50):
            return self._forward_image_release(event)
        else:
            return self._menu_release(event)

    def _get_forward_image(self):
        image_query = select(PhotoOrder).where(PhotoOrder.lost == False)
        last_image_ordering_id = self._image_ids[-1].ordering_id
        with RUNTIME_SESSION() as session:
            while True:
                if last_image_ordering_id is None:
                    new_image_query = image_query
                else:
                    new_image_query = image_query.where(PhotoOrder.id > last_image_ordering_id)

                new_image_row = session.scalars(
                    new_image_query.limit(1)
                ).one_or_none()

                if new_image_row is None:
                    if last_image_ordering_id is None:
                        break
                    else:
                        last_image_ordering_id = None
                else:
                    if new_image_row.id == self._image_ids[0].ordering_id:
                        break
                    last_image_ordering_id = new_image_row.id
                    new_image_id = _ImageIdPair(ordering_id=new_image_row.id, photo_id=new_image_row.photo_id)
                    photo_path = self._get_photo_paths(new_image_id)[0]
                    try:
                        new_image = PIL_Image.open(photo_path)
                    except FileNotFoundError:
                        logging.warning("Cannot find photo '%s'", photo_path)
                    except UnidentifiedImageError:
                        logging.warning("Unable to open file '%s'", photo_path)
                    else:
                        self._image_ids.append(new_image_id)
                        self._loaded_images.append(
                            PIL_ImageTk.PhotoImage(
                                _resize_image(
                                    new_image
                                )
                            )
                        )
                        return
                    session.execute(
                        update(PhotoOrder).where(PhotoOrder.id == new_image_id.ordering_id).values(lost=True)
                    )
                    session.commit()

        self._loaded_images.append(self._loaded_images.popleft())
        self._image_ids.append(self._image_ids.popleft())

    def _get_reverse_image(self):
        image_query = select(PhotoOrder).where(PhotoOrder.lost == False)
        last_image_ordering_id = self._image_ids[-1].ordering_id
        with RUNTIME_SESSION() as session:
            while True:
                if last_image_ordering_id is None:
                    new_image_query = image_query
                else:
                    new_image_query = image_query.where(PhotoOrder.id < last_image_ordering_id)

                new_image_row = session.scalars(
                    new_image_query.order_by(PhotoOrder.id.desc()).limit(1)
                ).one_or_none()

                if new_image_row is None:
                    if last_image_ordering_id is None:
                        break
                    else:
                        last_image_ordering_id = None
                else:
                    if new_image_row.id == self._image_ids[-1].ordering_id:
                        break
                    last_image_ordering_id = new_image_row.id
                    new_image_id = _ImageIdPair(ordering_id=new_image_row.id, photo_id=new_image_row.photo_id)
                    photo_path = self._get_photo_paths(new_image_id)[0]
                    try:
                        new_image = PIL_Image.open(photo_path)
                    except FileNotFoundError:
                        logging.warning("Cannot find photo '%s'", photo_path)
                    except UnidentifiedImageError:
                        logging.warning("Unable to open file '%s'", photo_path)
                    else:
                        self._image_ids.appendleft(new_image_id)
                        self._loaded_images.appendleft(
                            PIL_ImageTk.PhotoImage(
                                _resize_image(
                                    new_image
                                )
                            )
                        )
                        return
                    session.execute(
                        update(PhotoOrder).where(PhotoOrder.id == new_image_id.ordering_id).values(lost=True)
                    )
                    session.commit()

        self._loaded_images.appendleft(self._loaded_images.pop())
        self._image_ids.appendleft(self._image_ids.pop())

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
                if len(self._loaded_images) < 3:
                    self._switch_images()
                else:
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
                if len(self._loaded_images) < 3:
                    self._switch_images()
                else:
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

    def _switch_images(self):
        if len(self._loaded_images) != 2:
            raise Exception() # TODO: Better error message

        self._loaded_images.append(self._loaded_images.popleft())
        self._image_ids.append(self._image_ids.popleft())

        self._photo.configure(image=self._loaded_images[1])
        self._photo.image = self._loaded_images[1]

    def _switch_forward_image(self):
        self._get_forward_image()
        self._photo.configure(image=self._loaded_images[1])
        self._photo.image = self._loaded_images[1]

    def _switch_reverse_image(self):
        self._get_reverse_image()
        self._photo.configure(image=self._loaded_images[1])
        self._photo.image = self._loaded_images[1]

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

        self._switch_forward_image()

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
