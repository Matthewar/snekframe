"""Settings page"""

import datetime
import math
import subprocess
import json

from .analyse import load_photo_files, setup_viewed_photos
from .db import Settings, PhotoList, RUNTIME_SESSION, PERSISTENT_SESSION, RUNTIME_ENGINE, NumPhotos
from .fonts import FONTS
from .params import WINDOW_WIDTH

import tkinter as tk
import tkinter.ttk as ttk

from sqlalchemy.sql.expression import func, select, update, delete

class ShutdownWindow:
    def __init__(self, parent, firstrow=0, firstcolumn=0, grid_pady=5):
        self._countdown_id = None
        self._countdown_time = None

        self._shutdown_button = ttk.Button(parent, text="Shutdown", command=self._shutdown)
        self._restart_button = ttk.Button(parent, text="Restart", command=self._restart)
        self._shutdown_button.grid(row=firstrow, column=firstcolumn, rowspan=2)
        self._restart_button.grid(row=firstrow, column=firstcolumn+1, rowspan=2)

        self._info_text = tk.StringVar()
        self._info_label = ttk.Label(parent, textvariable=self._info_text)
        self._info_label.grid(row=firstrow, column=firstcolumn)
        self._cancel_button = ttk.Button(parent, text="Cancel", command=self._cancel)
        self._cancel_button.grid(row=firstrow, column=firstcolumn+1)

        self._info_label.grid_remove()
        self._cancel_button.grid_remove()

    def _update_info_text(self, shutdown=False, restart=False):
        if shutdown:
            info_text = "Shutting down"
        elif restart:
            info_text = "Restarting"
        time_remaining = self._countdown_time - datetime.datetime.now()
        seconds = int(math.ceil(time_remaining.total_seconds()))
        self._info_text.set(" ".join((info_text, "in", str(seconds), "seconds")))
        return seconds > 0

    def _shutdown_countdown(self):
        if self._countdown_id is None:
            return
        time_remaining = self._update_info_text(shutdown=True)
        if time_remaining:
            self._countdown_id = self._shutdown_button.after(300, self._shutdown_countdown)
        else:
            subprocess.run(["sudo", "shutdown", "0"])

    def _shutdown(self):
        self._shutdown_button.grid_remove()
        self._restart_button.grid_remove()
        self._info_label.grid()
        self._cancel_button.grid()
        self._countdown_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
        self._countdown_id = self._shutdown_button.after(300, self._shutdown_countdown)

    def _restart_countdown(self):
        if self._countdown_id is None:
            return
        time_remaining = self._update_info_text(restart=True)
        if time_remaining:
            self._countdown_id = self._shutdown_button.after(300, self._restart_countdown)
        else:
            subprocess.run(["sudo", "reboot"])

    def _restart(self):
        self._shutdown_button.grid_remove()
        self._restart_button.grid_remove()
        self._info_label.grid()
        self._cancel_button.grid()
        self._countdown_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
        self._countdown_id = self._shutdown_button.after(300, self._restart_countdown)

    def hidden(self):
        self._cancel()

    def _cancel(self):
        if self._countdown_id is not None:
            self._shutdown_button.after_cancel(self._countdown_id)
            self._countdown_id = None
        self._shutdown_button.grid()
        self._restart_button.grid()
        self._info_label.grid_remove()
        self._cancel_button.grid_remove()

class SettingsWindow:
    def __init__(self, frame, selection, destroy_display_window): # TODO: Previous screen if possible
        self._main_window = frame
        self._inner_window = ttk.Frame(self._main_window) # TODO: width
        self._photo_selection = selection
        self._destroy_display_window = destroy_display_window

        with PERSISTENT_SESSION() as session:
            all_settings = session.scalars(
                select(Settings).limit(1)
            ).one_or_none()

        photo_settings_title = ttk.Label(self._inner_window, text="Photo Settings", justify=tk.CENTER, font=FONTS.subtitle)
        photo_settings_title.grid(row=0, column=1, pady=(5, 10), columnspan=2)

        shuffle_photos_label = ttk.Label(self._inner_window, text="Shuffle:", justify=tk.LEFT, font=FONTS.default)
        shuffle_photos_label.grid(row=1, column=1, pady=5)

        shuffle_photos_frame = ttk.Frame(self._inner_window)
        shuffle_photos_frame.grid(row=1, column=2, pady=5)

        # TODO: If no photos, disable all shuffling?
        self._shuffle = tk.BooleanVar(value=all_settings.shuffle_photos)
        self._shuffle_on_button = tk.Radiobutton(shuffle_photos_frame, text="On", state=self._get_shuffle_on_state(), variable=self._shuffle, value=True, command=self._shuffle_button_callback, indicatoron=False)
        self._shuffle_off_button = tk.Radiobutton(shuffle_photos_frame, text="Off", state=self._get_shuffle_off_state(), variable=self._shuffle, value=False, command=self._shuffle_button_callback, indicatoron=False)
        self._shuffle_trigger_button = ttk.Button(shuffle_photos_frame, text="Reshuffle", state=self._get_shuffle_trigger_state(), command=self._trigger_shuffle)

        self._shuffle_on_button.grid(row=0, column=1)
        self._shuffle_off_button.grid(row=0, column=2)
        self._shuffle_trigger_button.grid(row=0, column=3)
        shuffle_photos_frame.grid_columnconfigure(0, weight=1)
        shuffle_photos_frame.grid_columnconfigure(4, weight=1)

        photos_info_label = ttk.Label(self._inner_window, text="Number of Photos:", justify=tk.LEFT, font=FONTS.default)
        photos_info_label.grid(row=2, column=1, pady=5)
        self._num_photos = tk.IntVar()
        self._num_photos.set(-1) # TODO: Move to constructor?
        num_photos_label = ttk.Label(self._inner_window, textvariable=self._num_photos, justify=tk.RIGHT, font=FONTS.default)
        num_photos_label.grid(row=2, column=2, pady=5)

        albums_info_label = ttk.Label(self._inner_window, text="Number of Albums:", justify=tk.LEFT, font=FONTS.default)
        albums_info_label.grid(row=3, column=1, pady=5)
        self._num_albums = tk.IntVar()
        self._num_albums.set(-1) # TODO: Move to constructor?
        num_albums_label = ttk.Label(self._inner_window, textvariable=self._num_albums, justify=tk.RIGHT, font=FONTS.default)
        num_albums_label.grid(row=3, column=2, pady=5)

        self._update_num_photos()

        rescan_photos_label = ttk.Label(self._inner_window, text="Rescan:", justify=tk.LEFT, font=FONTS.default)
        rescan_photos_label.grid(row=4, column=1, pady=5)

        # TODO: Add loading state
        rescan_photos_button = ttk.Button(self._inner_window, text="Go!", command=self._trigger_rescan)
        rescan_photos_button.grid(row=4, column=2, pady=5)

        system_settings_title = ttk.Label(self._inner_window, text="System Settings", justify=tk.CENTER, font=FONTS.subtitle)
        system_settings_title.grid(row=5, column=1, pady=(10, 10), columnspan=2)

        ip_addr_title_label = ttk.Label(self._inner_window, text="IP Address:", justify=tk.LEFT, font=FONTS.default)
        ip_addr_title_label.grid(row=6, column=1, pady=5)

        self._ip_addr = tk.StringVar()
        self._ip_addr_info_label = ttk.Label(self._inner_window, textvariable=self._ip_addr, justify=tk.RIGHT, font=FONTS.default)
        self._ip_addr_info_label.grid(row=6, column=2, pady=5)
        # TODO: Add refresh button
        self._get_ip_addr() # TODO: if displayed

        # TODO: Upgrade?

        self._shutdown_window = ShutdownWindow(self._inner_window, firstrow=7, firstcolumn=1, grid_pady=5)

        self._inner_window.grid_columnconfigure(0, weight=1)
        self._inner_window.grid_columnconfigure(9, weight=1)
        self._inner_window.place(x=0, y=0, width=WINDOW_WIDTH)

    def _get_shuffle_on_state(self):
        return "normal"

    def _get_shuffle_off_state(self):
        return "normal"

    def _get_shuffle_trigger_state(self):
        if not self._photo_selection.photos_selected or not self._shuffle.get():
            return "disabled"
        else:
            return "!disabled"

    def _shuffle_button_callback(self):
        self._shuffle_on_button.state([self._get_shuffle_on_state()])
        self._shuffle_off_button.state([self._get_shuffle_off_state()])
        self._shuffle_trigger_button.state([self._get_shuffle_trigger_state()])

        with PERSISTENT_SESSION() as session:
            result = session.execute(
                update(Settings).where(Settings.shuffle_photos != self._shuffle.get()).values(shuffle_photos=self._shuffle.get()).returning(Settings.id)
            ).one_or_none()
            session.commit()

        if result is not None:
            self._reorder_photos(shuffle=self._shuffle.get())

    def _trigger_shuffle(self): # TODO: Add counter/stop repeated calls?
        if not self._shuffle.get():
            return
        self._reorder_photos(shuffle=True)

    def _reorder_photos(self, shuffle=False): # TODO: Show some kind of info here. Need to rebuild display window
        if self._photo_selection.album_selected:
            album = self._photo_selection.album
        elif self._photo_selection.all_photos_selected:
            album = None
        else:
            # No photos selected
            return False

        return setup_viewed_photos(shuffle=shuffle, album=album)

    def _update_num_photos(self):
        with RUNTIME_SESSION() as session:
            result = session.scalars(
                select(NumPhotos).limit(1)
            ).one_or_none()

            if result is None:
                self._num_photos.set(-1)
                self._num_albums.set(-1)
            else:
                self._num_photos.set(result.num_photos)
                self._num_albums.set(result.num_albums)

    def _trigger_rescan(self):
        load_photo_files()
        found_photos = self._reorder_photos(shuffle=self._shuffle.get())
        if not found_photos:
            self._photo_selection.set_no_selection()
        self._shuffle_trigger_button.state([self._get_shuffle_trigger_state()])
        self._destroy_display_window()

    def _get_ip_addr(self):
        found_ip = False

        try:
            output_json = subprocess.run(
                ["ip", "-j", "-4", "addr", "show"],
                check=True,
                text=True,
                stdout=subprocess.PIPE).stdout
        except subprocess.CalledProcessError:
            pass
        else:
            for entry in json.loads(output_json):
                if entry["operstate"] == "UP":
                    addr_info = next((addr_info for addr_info in entry["addr_info"] if addr_info["family"] == "inet"), None)
                    if addr_info is not None:
                        found_ip = True
                        self._ip_addr.set(addr_info["local"])
                        break

        if not found_ip:
            self._ip_addr.set("Failed to find IP!")

        self._ip_addr_info_label.after(60*60*1000, self._get_ip_addr)

    def place(self, **place_kwargs):
        self._main_window.place(**place_kwargs)

    def place_forget(self):
        self._shutdown_window.hidden()
        self._main_window.place_forget()
