"""Settings page"""

import bisect
import datetime
import math
import subprocess
import json
import importlib.metadata
import tempfile
import os
import threading

from .analyse import load_photo_files, setup_viewed_photos
from .db import Settings, PhotoList, RUNTIME_SESSION, PERSISTENT_SESSION, RUNTIME_ENGINE, NumPhotos, get_database_version
from .fonts import FONTS
from . import params
from . import icons
from .params import WINDOW_WIDTH

import tkinter as tk
import tkinter.ttk as ttk

from sqlalchemy.sql.expression import func, select, update, delete

class SettingsContainer:
    """Runtime Accessible Settings"""
    def __init__(self):
        with PERSISTENT_SESSION() as session:
            result = session.scalars(
                select(Settings).limit(1)
            ).one_or_none()

        if result is None:
            raise Exception("No settings discovered")

        self._shuffle_photos = result.shuffle_photos
        self._sleep_start_time = result.sleep_start_time
        self._sleep_end_time = result.sleep_end_time
        self._photo_change_time = datetime.timedelta(seconds=result.photo_change_time)

    def _update_settings(self, **update_kwargs):
        with PERSISTENT_SESSION() as session:
            session.execute(
                update(Settings).values(**update_kwargs)
            )
            session.commit()

    @property
    def shuffle_photos(self):
        """Whether photos viewing order should be shuffled"""
        return self._shuffle_photos

    @shuffle_photos.setter
    def shuffle_photos(self, value):
        if not isinstance(value, bool):
            raise TypeError("shuffle_photos must be a boolean")
        self._shuffle_photos = value
        self._update_settings(shuffle_photos=value)

    @property
    def sleep_start_time(self):
        """Time when display sleep starts"""
        return self._sleep_start_time

    @sleep_start_time.setter
    def sleep_start_time(self, value):
        if value is not None and not isinstance(value, datetime.time):
            raise TypeError("sleep_start_time must be datetime.time")
        self._sleep_start_time = value
        self._update_settings(sleep_start_time=value)

    @property
    def sleep_end_time(self):
        """Time when display sleep ends"""
        return self._sleep_end_time

    @sleep_end_time.setter
    def sleep_end_time(self, value):
        if value is not None and not isinstance(value, datetime.time):
            raise TypeError("sleep_end_time must be datetime.time")
        self._sleep_end_time = value
        self._update_settings(sleep_end_time=value)

    @property
    def photo_change_time(self):
        """Frequency with which photos change"""
        return self._photo_change_time

    @photo_change_time.setter
    def photo_change_time(self, value):
        if isinstance(value, int):
            int_delay = value
            time_delay = datetime.timedelta(seconds=value)
        elif isinstance(value, datetime.timedelta):
            time_delay = value
            float_delay = time_delay.total_seconds()
            int_delay = int(float_delay)
            if int_delay != int(math.ceil(float_delay)):
                raise Exception("Photo change time cannot be less than seconds granularity")
        else:
            raise TypeError("photo_change_time must be an integer or datetime.delta")

        self._photo_change_time = time_delay
        self._update_settings(photo_change_time=int_delay)

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
            subprocess.run(["sudo", "/sbin/shutdown", "now"])

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
            subprocess.run(["sudo", "/sbin/reboot"])

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

    @property
    def rows(self):
        return 2

class SettingsWindow:
    def __init__(self, frame, selection, settings, destroy_display_window): # TODO: Previous screen if possible
        self._main_window = frame
        self._inner_window = ttk.Frame(self._main_window) # TODO: width
        self._photo_selection = selection
        self._settings_selection = settings
        self._destroy_display_window = destroy_display_window

        row = 0
        LEFTCOLUMN = 1
        RIGHTCOLUMN = LEFTCOLUMN + 1
        COLUMNSPAN = RIGHTCOLUMN - LEFTCOLUMN + 1

        photo_settings_title = ttk.Label(self._inner_window, text="Photo Settings", justify=tk.CENTER, font=FONTS.subtitle)
        photo_settings_title.grid(row=row, column=LEFTCOLUMN, pady=(5, 10), columnspan=COLUMNSPAN)
        row += 1

        shuffle_photos_label = ttk.Label(self._inner_window, text="Shuffle:", justify=tk.LEFT, font=FONTS.default)
        shuffle_photos_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        shuffle_photos_frame = ttk.Frame(self._inner_window)
        shuffle_photos_frame.grid(row=row, column=RIGHTCOLUMN, pady=5)

        # TODO: If no photos, disable all shuffling?
        self._shuffle = tk.BooleanVar(value=self._settings_selection.shuffle_photos)
        self._shuffle_on_button = tk.Radiobutton(shuffle_photos_frame, text="On", state=self._get_shuffle_on_state(), variable=self._shuffle, value=True, command=self._shuffle_button_callback, indicatoron=False, font=FONTS.default)
        self._shuffle_off_button = tk.Radiobutton(shuffle_photos_frame, text="Off", state=self._get_shuffle_off_state(), variable=self._shuffle, value=False, command=self._shuffle_button_callback, indicatoron=False, font=FONTS.default)
        self._shuffle_trigger_button = ttk.Button(shuffle_photos_frame, image=icons.ICONS.get("shuffle"), text="Reshuffle", state=self._get_shuffle_trigger_state(), command=self._trigger_shuffle)

        self._shuffle_on_button.grid(row=0, column=1)
        self._shuffle_off_button.grid(row=0, column=2)
        self._shuffle_trigger_button.grid(row=0, column=3)
        shuffle_photos_frame.grid_columnconfigure(0, weight=1)
        shuffle_photos_frame.grid_columnconfigure(4, weight=1)

        row += 1

        photo_transition_label = ttk.Label(self._inner_window, text="Photo Transition Time", justify=tk.LEFT, font=FONTS.default)
        photo_transition_label.grid(row=row, column=LEFTCOLUMN, pady=5)
        photo_transition_controls = ttk.Frame(self._inner_window)
        photo_transition_controls.grid(row=row, column=RIGHTCOLUMN, pady=5)

        self._decrease_transition_time_button = ttk.Button(photo_transition_controls, image=icons.ICONS.get("minus"), text="-", state=self._get_transition_minus_state(), command=self._transition_decrease_callback)
        self._transition_time = tk.StringVar()
        self._set_transition_time_string()
        self._transition_time_display = ttk.Label(photo_transition_controls, textvariable=self._transition_time, font=FONTS.default)
        self._increase_transition_time_button = ttk.Button(photo_transition_controls, image=icons.ICONS.get("plus"), text="+", state=self._get_transition_plus_state(), command=self._transition_increase_callback)

        self._decrease_transition_time_button.grid(row=0, column=1)
        self._transition_time_display.grid(row=0, column=2)
        self._increase_transition_time_button.grid(row=0, column=3)
        photo_transition_controls.grid_columnconfigure(0, weight=1)
        photo_transition_controls.grid_columnconfigure(4, weight=1)

        row += 1

        photos_info_label = ttk.Label(self._inner_window, text="Number of Photos:", justify=tk.LEFT, font=FONTS.default)
        photos_info_label.grid(row=row, column=LEFTCOLUMN, pady=5)
        self._num_photos = tk.IntVar()
        self._num_photos.set(-1) # TODO: Move to constructor?
        num_photos_label = ttk.Label(self._inner_window, textvariable=self._num_photos, justify=tk.RIGHT, font=FONTS.default)
        num_photos_label.grid(row=row, column=RIGHTCOLUMN, pady=5)
        row += 1

        albums_info_label = ttk.Label(self._inner_window, text="Number of Albums:", justify=tk.LEFT, font=FONTS.default)
        albums_info_label.grid(row=row, column=LEFTCOLUMN, pady=5)
        self._num_albums = tk.IntVar()
        self._num_albums.set(-1) # TODO: Move to constructor?
        num_albums_label = ttk.Label(self._inner_window, textvariable=self._num_albums, justify=tk.RIGHT, font=FONTS.default)
        num_albums_label.grid(row=row, column=RIGHTCOLUMN, pady=5)
        row += 1

        self._update_num_photos()

        rescan_photos_label = ttk.Label(self._inner_window, text="Rescan:", justify=tk.LEFT, font=FONTS.default)
        rescan_photos_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        # TODO: Add loading state
        rescan_photos_button = ttk.Button(self._inner_window, text="Go!", command=self._trigger_rescan)
        rescan_photos_button.grid(row=row, column=RIGHTCOLUMN, pady=5)
        row += 1

        system_settings_title = ttk.Label(self._inner_window, text="System Settings", justify=tk.CENTER, font=FONTS.subtitle)
        system_settings_title.grid(row=row, column=LEFTCOLUMN, pady=(10, 10), columnspan=COLUMNSPAN)
        row += 1

        ip_addr_title_label = ttk.Label(self._inner_window, text="IP Address:", justify=tk.LEFT, font=FONTS.default)
        ip_addr_title_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        self._ip_addr = tk.StringVar()
        self._ip_addr_info_label = ttk.Label(self._inner_window, textvariable=self._ip_addr, justify=tk.RIGHT, font=FONTS.default)
        self._ip_addr_info_label.grid(row=row, column=RIGHTCOLUMN, pady=5)
        # TODO: Add refresh button
        self._get_ip_addr() # TODO: if displayed
        row += 1

        self._shutdown_window = ShutdownWindow(self._inner_window, firstrow=row, firstcolumn=LEFTCOLUMN, grid_pady=5)
        row += self._shutdown_window.rows

        current_db_version_label = ttk.Label(self._inner_window, text="Current Database Version:", justify=tk.LEFT, font=FONTS.default)
        current_db_version_label.grid(row=row, column=LEFTCOLUMN, pady=5)
        db_version_label = ttk.Label(self._inner_window, text="v%d.%d" % get_database_version(), justify=tk.RIGHT, font=FONTS.default)
        db_version_label.grid(row=row, column=RIGHTCOLUMN, pady=5)
        row += 1

        current_version_string = importlib.metadata.version("snekframe")
        self._current_version = tuple(current_version_string.split('.'))
        current_version_label = ttk.Label(self._inner_window, text="Current Version:", justify=tk.LEFT, font=FONTS.default)
        current_version_label.grid(row=row, column=LEFTCOLUMN, pady=5)
        version_label = ttk.Label(self._inner_window, text=current_version_string, justify=tk.RIGHT, font=FONTS.default)
        version_label.grid(row=row, column=RIGHTCOLUMN, pady=5)
        row += 1

        upgrade_label = ttk.Label(self._inner_window, text="Upgrade Available:", justify=tk.LEFT, font=FONTS.default)
        upgrade_label.grid(row=row, column=LEFTCOLUMN, pady=5)
        upgrade_frame = ttk.Frame(self._inner_window)
        upgrade_frame.grid(row=row, column=RIGHTCOLUMN, pady=5)

        self._upgrade_info_text = None
        self._upgrade_info = tk.StringVar()
        self._upgrade_available = None
        self._upgrade_check_thread = None

        upgrade_info_label = ttk.Label(upgrade_frame, textvariable=self._upgrade_info, justify=tk.RIGHT, font=FONTS.default)
        upgrade_info_label.grid(row=0, column=0)
        self._upgrade_button = ttk.Button(upgrade_frame, text="Upgrade", state=self._get_upgrade_button_state(), command=self._run_upgrade)
        self._upgrade_button.grid(row=0, column=1)
        check_upgrade_button = ttk.Button(upgrade_frame, text="Check for upgrade", command=self._check_upgrade)
        check_upgrade_button.grid(row=0, column=2)
        self._check_upgrade()

        row += 1

        self._inner_window.grid_columnconfigure(0, weight=1)
        self._inner_window.grid_columnconfigure(RIGHTCOLUMN+1, weight=1)
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
        self._shuffle_on_button.configure(state=self._get_shuffle_on_state())
        self._shuffle_off_button.configure(state=self._get_shuffle_off_state())
        self._shuffle_trigger_button.state([self._get_shuffle_trigger_state()])

        if self._shuffle.get() != self._settings_selection.shuffle_photos:
            self._settings_selection.shuffle_photos = self._shuffle.get()
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

    _TRANSITION_TIMES = (
        datetime.timedelta(seconds=10),
        datetime.timedelta(seconds=15),
        datetime.timedelta(seconds=30),
        datetime.timedelta(minutes=1),
        datetime.timedelta(minutes=2),
        datetime.timedelta(minutes=5),
        datetime.timedelta(minutes=10),
        datetime.timedelta(minutes=15),
        datetime.timedelta(minutes=30),
        datetime.timedelta(hours=1),
        datetime.timedelta(hours=2),
    )

    def _get_transition_minus_state(self):
        if self._settings_selection.photo_change_time <= self._TRANSITION_TIMES[0]:
            return "disabled"
        else:
            return "!disabled"

    def _get_transition_plus_state(self):
        if self._settings_selection.photo_change_time >= self._TRANSITION_TIMES[-1]:
            return "disabled"
        else:
            return "!disabled"

    def _set_transition_time_string(self):
        seconds = self._settings_selection.photo_change_time.total_seconds()
        info = []
        hours = int(seconds / 3600)
        if hours == 1:
            info.append("1 hour")
        elif hours > 1:
            info.append(f"{hours} hours")
        seconds = seconds % 3600
        minutes = int(seconds / 60)
        if minutes == 1:
            info.append("1 minute")
        elif minutes > 1:
            info.append(f"{minutes} minutes")
        seconds = int(seconds % 60)
        if seconds == 1:
            info.append("1 second")
        elif seconds > 1:
            info.append(f"{seconds} seconds")

        self._transition_time.set(", ".join(info))

    def _transition_decrease_callback(self):
        position = bisect.bisect_left(self._TRANSITION_TIMES, self._settings_selection.photo_change_time)
        if position > 0:
            position -= 1
            self._settings_selection.photo_change_time = self._TRANSITION_TIMES[position]
            self._set_transition_time_string()
        self._decrease_transition_time_button.state([self._get_transition_minus_state()])
        self._increase_transition_time_button.state([self._get_transition_plus_state()])

    def _transition_increase_callback(self):
        position = bisect.bisect_right(self._TRANSITION_TIMES, self._settings_selection.photo_change_time)
        if position < len(self._TRANSITION_TIMES):
            self._settings_selection.photo_change_time = self._TRANSITION_TIMES[position]
            self._set_transition_time_string()
        self._decrease_transition_time_button.state([self._get_transition_minus_state()])
        self._increase_transition_time_button.state([self._get_transition_plus_state()])

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
        self._destroy_display_window() # TODO: Redraw photo select window

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

    def _get_upgrade_button_state(self):
        if self._upgrade_available is None:
            return "disabled"
        else:
            return "!disabled"

    def _run_upgrade(self):
        if self._upgrade_available is None:
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(["git", "clone", params.REPO_URL], cwd=temp_dir)
            REPO_DIR = os.path.join(temp_dir, params.REPO_NAME)
            subprocess.run(["git", "checkout", "v{}".format(".".join(self._upgrade_available))], cwd=REPO_DIR)
            query_version = subprocess.run(["python3", "-c", "from setuptools import setup; setup()", "--version"], cwd=REPO_DIR, stdout=subprocess.PIPE, text=True)
            queried_version = tuple(query_version.stdout.rstrip('\n').lstrip('v').split('.')[0:3])
            if queried_version != self._upgrade_available:
                raise Exception("queried version {} doesn't match expected upgrade {}".format(queried_version, self._upgrade_available))
            subprocess.run([os.path.join(params.FILES_LOCATION, params.VIRTUALENV_NAME, "bin", "pip"), "install", "./snekframe"], cwd=temp_dir)
        subprocess.run(["sudo", "/sbin/reboot"])

    def _check_upgrade(self):
        if self._upgrade_check_thread is not None:
            self._upgrade_info.set("Error: Program in bad state")
            return
        self._upgrade_button.state(["disabled"])
        self._upgrade_available = None
        self._upgrade_info.set("Checking for new versions")
        self._upgrade_check_thread = threading.Thread(target=self._thread_check_upgrade)
        self._upgrade_check_thread.start()
        self._check_upgrade_complete()

    def _check_upgrade_complete(self):
        if self._upgrade_check_thread.is_alive():
            self._upgrade_button.after(100, self._check_upgrade_complete)
        else:
            self._upgrade_button.state([self._get_upgrade_button_state()])
            self._upgrade_info.set(self._upgrade_info_text)
            self._upgrade_check_thread = None

    def _thread_check_upgrade(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(["git", "clone", params.REPO_URL], cwd=temp_dir)
            REPO_DIR = os.path.join(temp_dir, params.REPO_NAME)
            get_tags = subprocess.run(["git", "tag", "--sort=creatordate"], cwd=REPO_DIR, stdout=subprocess.PIPE, text=True)
            all_tags = get_tags.stdout.rstrip('\n').split('\n')
        if not all_tags or (len(all_tags) == 1 and all_tags[0] == ''):
            self._upgrade_info_text = "Unable to find any versions!"
            self._upgrade_available = None
        else:
            latest_major, latest_minor, latest_patch = all_tags[-1].lstrip('v').split('.')[0:3]
            if (latest_major, latest_minor, latest_patch) == self._current_version:
                self._upgrade_info_text = "Already on latest version"
                self._upgrade_available = None
            elif (latest_major, latest_minor, latest_patch) < self._current_version:
                self._upgrade_info_text = f"Error: Latest reported version (v{latest_major}.{latest_minor}) is older than current version"
                self._upgrade_available = None
            else:
                self._upgrade_info_text = f"Version v{latest_major}.{latest_minor}.{latest_patch} now available"
                self._upgrade_available = (latest_major, latest_minor, latest_patch)

    def place(self, **place_kwargs):
        self._main_window.place(**place_kwargs)

    def place_forget(self):
        self._shutdown_window.hidden()
        self._main_window.place_forget()
