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
from enum import Enum, auto

from .db import SettingsV0, PERSISTENT_SESSION
from .db.version import get_database_version
from .fonts import FONTS
from . import params
from . import elements
from .params import WINDOW_WIDTH, WINDOW_HEIGHT, TITLE_BAR_HEIGHT

import tkinter as tk
from tkinter import ttk

from sqlalchemy.sql.expression import select, update

class SettingsContainer:
    """Runtime Accessible Settings"""
    def __init__(self):
        with PERSISTENT_SESSION() as session:
            result = session.scalars(
                select(SettingsV0).limit(1)
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
                update(SettingsV0).values(**update_kwargs)
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

class SettingsMenu(elements.LimitedFrameBaseElement):
    """Sidebar menu for various settings pages"""
    def __init__(self, parent, open_photo_settings, open_system_settings, open_display_settings):
        super().__init__(parent, {})

        menu_buttons = elements.RadioButtonSet(default_button_cls=elements.IconTextRadioButton)

        self._photo_settings_button = menu_buttons.add_button(self._frame, open_photo_settings, text="Photos", icon_name="photo", selected=False)
        button_elements = (
            self._photo_settings_button,
            menu_buttons.add_button(self._frame, open_system_settings, text="System", icon_name="system", selected=False),
            menu_buttons.add_button(self._frame, open_display_settings, text="Display", icon_name="display", selected=False),
        )

        for row, element in enumerate(button_elements):
            element.grid(row=row, column=0, sticky="ew")

        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_rowconfigure(len(button_elements), weight=1)

    def reset(self):
        """Bring to default viewstate"""
        self._photo_settings_button.invoke()

class PhotoShuffleSettings(elements.LimitedFrameBaseElement):
    def __init__(self, parent, settings_container, reorder_photos, destroy_photo_window):
        super().__init__(parent, {})

        shuffle_buttons = elements.RadioButtonSet(default_button_cls=elements.TextRadioButton)

        def reshuffle_photos():
            reorder_photos()
            destroy_photo_window(display_window=True, selection_window=False)

        reshuffle_button = elements.IconButton(self._frame, reshuffle_photos, "shuffle", enabled=settings_container.shuffle_photos)
        reshuffle_button.grid(row=0, column=5)

        def unshuffle_photos():
            settings_container.shuffle_photos = False
            reshuffle_button.enabled = False
            reshuffle_photos() # This uses the shuffle setting which we've set to false

        shuffle_off_button = shuffle_buttons.add_button(self._frame, unshuffle_photos, selected=not settings_container.shuffle_photos, text="Off")
        shuffle_off_button.grid(row=0, column=1)

        def shuffle_photos():
            settings_container.shuffle_photos = True
            reshuffle_button.enabled = True
            reshuffle_button.invoke()

        shuffle_on_button = shuffle_buttons.add_button(self._frame, shuffle_photos, selected=settings_container.shuffle_photos, text="On")
        shuffle_on_button.grid(row=0, column=3)

        self._frame.grid_columnconfigure(0, weight=2)
        self._frame.grid_columnconfigure(2, weight=1)
        self._frame.grid_columnconfigure(4, weight=1)
        self._frame.grid_columnconfigure(6, weight=2)

class PhotoTransitionSettings(elements.LimitedFrameBaseElement):

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

    def __init__(self, parent, settings_container):
        super().__init__(parent, {})

        self._settings_container = settings_container

        self._decrease_time_button = elements.IconButton(self._frame, self._decrease_time, "minus", enabled=self._can_decrease_time())
        self._decrease_time_button.place(x=0, rely=0.5, anchor="w")

        self._time_info = elements.UpdateLabel(self._frame, initialtext=self._get_transition_time_string())
        self._time_info.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._increase_time_button = elements.IconButton(self._frame, self._increase_time, "plus", enabled=self._can_increase_time())
        self._increase_time_button.place(relx=1.0, rely=0.5, anchor="e")

    def _can_increase_time(self):
        return self._settings_container.photo_change_time < self._TRANSITION_TIMES[-1]

    def _can_decrease_time(self):
        return self._settings_container.photo_change_time > self._TRANSITION_TIMES[0]

    def _decrease_time(self):
        position = bisect.bisect_left(self._TRANSITION_TIMES, self._settings_container.photo_change_time)
        if position > 0:
            position -= 1
            self._settings_container.photo_change_time = self._TRANSITION_TIMES[position]
            self._time_info.text = self._get_transition_time_string()

        self._decrease_time_button.enabled = position != 0
        self._increase_time_button.enabled = True

    def _increase_time(self):
        position = bisect.bisect_right(self._TRANSITION_TIMES, self._settings_container.photo_change_time)
        if position < len(self._TRANSITION_TIMES):
            self._settings_container.photo_change_time = self._TRANSITION_TIMES[position]
            self._time_info.text = self._get_transition_time_string()

        self._increase_time_button.enabled = self._can_increase_time()
        self._decrease_time_button.enabled = True

    def _get_transition_time_string(self):
        seconds = self._settings_container.photo_change_time.total_seconds()
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

        return ", ".join(info)

class PhotoSettings(elements.LimitedFrameBaseElement):
    def __init__(self, parent, settings_container, photos_container, destroy_photo_window):
        super().__init__(parent, {})

        self._settings_container = settings_container
        self._photos_container = photos_container
        self._destroy_photo_window = destroy_photo_window

        row = 1
        LEFTCOLUMN = 1
        RIGHTCOLUMN = LEFTCOLUMN + 1

        shuffle_photos_label = ttk.Label(self._frame, text="Shuffle:", justify=tk.LEFT, font=FONTS.default)
        shuffle_photos_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5, sticky="ew")

        def _reorder_photos(self):
            self._photos_container.reorder(self._settings_container.shuffle_photos)

        shuffle_photos_settings = PhotoShuffleSettings(self._frame, settings_container, _reorder_photos, destroy_photo_window)
        shuffle_photos_settings.grid(row=row, column=RIGHTCOLUMN, padx=25, pady=5, sticky="snew")

        row += 1

        photo_transition_label = ttk.Label(self._frame, text="Photo Transition Time:", justify=tk.LEFT, font=FONTS.default)
        photo_transition_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5, sticky="ew")

        photo_transition_controls = PhotoTransitionSettings(self._frame, settings_container)
        photo_transition_controls.grid(row=row, column=RIGHTCOLUMN, padx=25, pady=5, sticky="snew")

        row += 1

        photos_info_label = ttk.Label(self._frame, text="Number of Photos:", justify=tk.LEFT, font=FONTS.default)
        photos_info_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5, sticky="ew")

        self._num_photos_label = elements.UpdateLabel(self._frame, initialtext="Loading", justify=tk.RIGHT, font=FONTS.default)
        self._num_photos_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        albums_info_label = ttk.Label(self._frame, text="Number of Albums:", justify=tk.LEFT, font=FONTS.default)
        albums_info_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5, sticky="ew")
        self._num_albums_label = elements.UpdateLabel(self._frame, initialtext="Loading", justify=tk.RIGHT, font=FONTS.default)
        self._num_albums_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        self._update_num_photo_labels()

        row += 1

        rescan_photos_label = ttk.Label(self._frame, text="Rescan:", justify=tk.LEFT, font=FONTS.default)
        rescan_photos_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5, sticky="ew")

        rescan_photos_button = elements.TextButton(self._frame, self._trigger_rescan, text="Go!")
        rescan_photos_button.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        self._frame.grid_columnconfigure(LEFTCOLUMN, weight=1)
        self._frame.grid_columnconfigure(RIGHTCOLUMN, weight=2)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(row, weight=1)

    def _update_num_photo_labels(self):
        """Update the labels with number of photos"""
        self._num_photos_label.text = str(self._photos_container.num_photos)
        self._num_albums_label.text = str(self._photos_container.num_directories)

    def _trigger_rescan(self):
        """Rescan directory for photos"""
        # TODO: Add threading? Need to block moving off this screen if so
        self._photos_container.rescan(shuffle=self._settings_container.shuffle_photos)
        self._destroy_photo_window()
        self._update_num_photo_labels()

class AutoUpdateIPLabel(elements.AutoUpdateLabel):
    """Label with IP address that auto update"""
    UPDATE_CALLBACK_MIN_TIME_MS = 60*60*1000 # Check every hour
    # TODO: Add refresh button?

    def _update_label(self):
        """Get current IP address and update text"""
        self.text = self._get_ip_addr()

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
                        return addr_info["local"]

        if not found_ip:
            return "Failed to find IP!"

class _SystemCallWindow(elements.LimitedFrameBaseElement):
    """Window to manage a shutdown or restart"""
    def __init__(self, parent, button_command_text, info_display_text):
        super().__init__(parent, {})

        self._info_display_text = info_display_text

        self._countdown_job_id = None
        self._countdown_end_time = None

        self._linked_windows = [] # Only one system call window can work at a time

        self._button = elements.TextToggleButton(self._frame, self._start_countdown, self.cancel, text=button_command_text, selected_text="Cancel")
        self._button.grid(row=0, column=0, padx=10)

        self._label = elements.UpdateLabel(self._frame, initialtext="")
        self._label.grid(row=0, column=1, padx=20)

        self._frame.grid_columnconfigure(2, weight=1)

    def link_window(self, window):
        if not isinstance(window, _SystemCallWindow):
            raise TypeError()
        self._linked_windows.append(window)

    def enable(self):
        self._button.enabled = True

    def disable(self):
        self.cancel()
        self._button.disabled = False

    def place_forget(self):
        # TODO Cancel countdown
        super().place_forget()

    def _start_countdown(self):
        for window in self._linked_windows:
            window.disable()

        self._countdown_end_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
        self._continue_countdown()

    def _continue_countdown(self):
        time_remaining = self._countdown_end_time - datetime.datetime.now()
        seconds = int(math.ceil(time_remaining.total_seconds()))
        self._label.text = " ".join((self._info_display_text, "in", str(seconds), "seconds"))

        if seconds > 0:
            self._countdown_job_id = self._frame.after(300, self._continue_countdown)
        elif not self._system_call():
            self.cancel()
            self._label.text = "Failed to run command!"

    def cancel(self):
        if self._countdown_job_id is not None:
            self._frame.after_cancel(self._countdown_job_id)
            self._countdown_job_id = None
        self._label.text = ""
        self._button.selected = False

        for window in self._linked_windows:
            window.enable()

    def _system_call(self):
        raise NotImplementedError()

class _ShutdownCallWindow(_SystemCallWindow):
    def __init__(self, parent):
        super().__init__(parent, "Shutdown", "Shutting down")

    def _system_call(self):
        try:
            subprocess.run(["sudo", "/sbin/shutdown", "now"], check=True)
        except subprocess.CalledProcessError:
            return False
        return True

class _RestartCallWindow(_SystemCallWindow):
    def __init__(self, parent):
        super().__init__(parent, "Restart", "Restarting")

    def _system_call(self):
        try:
            subprocess.run(["sudo", "/sbin/reboot"], check=True)
        except subprocess.CalledProcessError:
            return False
        return True

class SystemSettings(elements.LimitedFrameBaseElement):
    def __init__(self, parent):
        super().__init__(parent, {})

        row = 1
        LEFTCOLUMN = 1
        RIGHTCOLUMN = LEFTCOLUMN + 1
        COLUMNSPAN = RIGHTCOLUMN - LEFTCOLUMN + 1

        ip_addr_title_label = ttk.Label(self._frame, text="IP Address:", justify=tk.LEFT, font=FONTS.default)
        ip_addr_title_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5, sticky="ew")

        self._ip_addr_info_label = AutoUpdateIPLabel(self._frame, justify=tk.RIGHT, font=FONTS.default) # TODO: Add loading initial text?
        self._ip_addr_info_label.grid(row=row, column=RIGHTCOLUMN, padx=25, pady=5)

        row += 1

        self._shutdown_window = _ShutdownCallWindow(self._frame)
        self._shutdown_window.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN, padx=25, sticky="snew")

        row += 1

        self._restart_window = _RestartCallWindow(self._frame)
        self._restart_window.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN, padx=25, sticky="snew")

        self._shutdown_window.link_window(self._restart_window)
        self._restart_window.link_window(self._shutdown_window)

        row += 1

        current_db_version_label = ttk.Label(self._frame, text="Current Database Version:", justify=tk.LEFT, font=FONTS.default)
        current_db_version_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5)

        db_version_label = ttk.Label(self._frame, text="v{:d}.{:d}".format(*get_database_version()), justify=tk.RIGHT, font=FONTS.default)
        db_version_label.grid(row=row, column=RIGHTCOLUMN, padx=25, pady=5)

        row += 1

        current_version_string = importlib.metadata.version("snekframe")
        self._current_version = tuple(current_version_string.split('.'))

        current_version_label = ttk.Label(self._frame, text="Current Version:", justify=tk.LEFT, font=FONTS.default)
        current_version_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5)

        version_label = ttk.Label(self._frame, text=current_version_string, justify=tk.RIGHT, font=FONTS.default)
        version_label.grid(row=row, column=RIGHTCOLUMN, padx=25, pady=5)

        row += 1

        upgrade_label = ttk.Label(self._frame, text="Upgrade Available:", justify=tk.LEFT, font=FONTS.default)
        upgrade_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5)

        self._upgrade_info_label = elements.UpdateLabel(self._frame)
        self._upgrade_info_label.grid(row=row, column=RIGHTCOLUMN, padx=25, pady=5)

        row += 1

        self._upgrade_info_text = None
        self._upgrade_available = None # Version available
        self._upgrade_check_thread = None

        self._upgrade_button = elements.TextButton(self._frame, text="Upgrade", enabled=False, command=self._run_upgrade)
        self._upgrade_button.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN, pady=5)

        row += 1

        self._check_upgrade_button = elements.TextButton(self._frame, text="Check for upgrade", command=self._check_upgrade)
        self._check_upgrade_button.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN, pady=5)
        self._check_upgrade_button.invoke()
        self._check_upgrade()

        row += 1

        self._frame.grid_columnconfigure(LEFTCOLUMN, weight=1)
        self._frame.grid_columnconfigure(RIGHTCOLUMN, weight=2)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(row, weight=1)

    def place(self, unpause_ip=True, **place_kwargs):
        if unpause_ip:
            self._ip_addr_info_label.update_label()
        super().place(**place_kwargs)

    def place_forget(self, pause_ip=True):
        if pause_ip:
            self._ip_addr_info_label.pause_updates()

        self._shutdown_window.cancel()
        self._restart_window.cancel()

        super().place_forget()

    def _run_upgrade(self):
        if self._upgrade_available is None:
            return

        self._upgrade_button.enabled = False
        self._check_upgrade_button.enabled = False
        upgrade_version_string = "v{}".format(".".join(self._upgrade_available))
        self._upgrade_info_label.text = f"Upgrading to version {upgrade_version_string}"

        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(["git", "clone", params.REPO_URL], cwd=temp_dir)
            REPO_DIR = os.path.join(temp_dir, params.REPO_NAME)
            subprocess.run(["git", "checkout", upgrade_version_string], cwd=REPO_DIR)
            query_version = subprocess.run(["python3", "-c", "from setuptools import setup; setup()", "--version"], cwd=REPO_DIR, stdout=subprocess.PIPE, text=True)
            queried_version = tuple(query_version.stdout.rstrip('\n').lstrip('v').split('.')[0:3])
            if queried_version != self._upgrade_available:
                raise Exception("queried version {} doesn't match expected upgrade {}".format(queried_version, self._upgrade_available))
            subprocess.run([os.path.join(params.FILES_LOCATION, params.VIRTUALENV_NAME, "bin", "pip"), "install", "./snekframe"], cwd=temp_dir)
        subprocess.run(["sudo", "/sbin/reboot"])

    def _check_upgrade(self):
        if self._upgrade_check_thread is not None:
            self._upgrade_info_label.text = "Error: Program in bad state"
            return

        self._upgrade_button.enabled = False
        self._check_upgrade_button.enabled = False
        self._upgrade_available = None
        self._upgrade_info_label.text = "Checking for new versions"
        self._upgrade_check_thread = threading.Thread(target=self._thread_check_upgrade)
        self._upgrade_check_thread.start()
        self._check_upgrade_complete()

    def _check_upgrade_complete(self):
        if self._upgrade_check_thread.is_alive():
            self._upgrade_button.after(100, self._check_upgrade_complete)
        else:
            self._check_upgrade_button.enabled = True
            if self._upgrade_available is not None:
                self._upgrade_button.enabled = True
            self._upgrade_info_label.text = self._upgrade_info_text
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

class BrightnessSettings(elements.LimitedFrameBaseElement):
    def __init__(self, parent):
        super().__init__(parent, {})

        self._decrease_brightness_button = elements.IconButton(self._frame, self._decrement_brightness, "minus", enabled=False)
        self._current_brightness = elements.UpdateLabel(self._frame, initialtext=0, variabletype=tk.IntVar, style="Default")
        self._max_brightness = elements.UpdateLabel(self._frame, initialtext=0, variabletype=tk.IntVar, style="Default")
        self._increase_brightness_button = elements.IconButton(self._frame, self._increment_brightness, "plus", enabled=False)

        self._get_brightness()

        columns = (
            self._decrease_brightness_button,
            ttk.Label(self._frame, text="0", font=FONTS.default),
            self._current_brightness,
            self._max_brightness,
            self._increase_brightness_button,
        )

        column = 0
        for element in columns:
            self._frame.grid_columnconfigure(column, weight=1)
            column += 1
            element.grid(row=0, column=column, padx=25)
            column += 1
        self._frame.grid_columnconfigure(column, weight=1)

    def _get_brightness(self):
        brightness_info = subprocess.run(["ddcutil", "-t", "getvcp", "10"], check=True, text=True, stdout=subprocess.PIPE).stdout.rstrip().split(' ')
        # 0 - VCP
        # 1 - <Code>
        # 2 - C
        # 3 - <Current Value>
        # 4 - <Max Brightness>
        self._current_brightness.text = brightness_info[3]
        self._max_brightness.text = brightness_info[4]

        self._decrease_brightness_button.enabled = self._can_decrease_brightness()
        self._increase_brightness_button.enabled = self._can_increase_brightness()

    def _can_increase_brightness(self):
        return self._current_brightness.text < self._max_brightness.text

    def _can_decrease_brightness(self):
        return self._current_brightness.text > 0

    def _set_brightness(self, value : int):
        if not isinstance(value, int):
            raise TypeError("Brightness value must be an integer")

        if value >= 0 and value <= self._max_brightness.text:
            brightness_result = subprocess.run(["ddcutil", "-t", "setvcp", "10", f"{value:d}"], check=True, text=True)
            self._current_brightness.text = value
            self._decrease_brightness_button.enabled = self._can_decrease_brightness()
            self._increase_brightness_button.enabled = self._can_increase_brightness()

    def _increment_brightness(self):
        self._set_brightness(self._current_brightness.text + 5)

    def _decrement_brightness(self):
        self._set_brightness(self._current_brightness.text - 5)

class DisplaySettings(elements.LimitedFrameBaseElement):
    def __init__(self, parent):
        super().__init__(parent, {})

        row = 1
        LEFTCOLUMN = 0
        RIGHTCOLUMN = 1

        brightness_label = ttk.Label(self._frame, text="Brightness:", justify=tk.LEFT, font=FONTS.default)
        brightness_label.grid(row=row, column=LEFTCOLUMN, padx=(25, 0), pady=5, sticky="ew")

        brightness_settings = BrightnessSettings(self._frame)
        brightness_settings.grid(row=row, column=RIGHTCOLUMN, padx=25, pady=5, sticky="snew")

        row += 1

        self._frame.grid_columnconfigure(LEFTCOLUMN, weight=1)
        self._frame.grid_columnconfigure(RIGHTCOLUMN, weight=2)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(row, weight=1)

class SettingsWindow:
    class OpenWindow(Enum):
        Photo = auto()
        System = auto()
        Display = auto()

    _MENU_WIDTH = 300

    def __init__(self, parent, photos_container, settings, destroy_photo_window): # TODO: Previous screen if possible
        self._main_window = ttk.Frame(master=parent)

        self._menu = SettingsMenu(self._main_window, self._open_photo_settings, self._open_system_settings, self._open_display_settings)
        self._menu.place(x=0, y=0, anchor="nw", height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT, width=self._MENU_WIDTH)
        self._current_window = None

        self._photos_container = photos_container
        self._settings_container = settings
        self._destroy_photo_window = destroy_photo_window

        self._photo_window = PhotoSettings(self._main_window, self._settings_container, self._photos_container, self._destroy_photo_window)
        self._system_window = SystemSettings(self._main_window)
        self._display_window = DisplaySettings(self._main_window)

    def _close_current_window(self):
        if self._current_window is None:
            return # Skip, should only occur on startup
        if self._current_window == self.OpenWindow.Photo:
            self._photo_window.place_forget()
        elif self._current_window == self.OpenWindow.System:
            self._system_window.place_forget()
        elif self._current_window == self.OpenWindow.Display:
            self._display_window.place_forget()
        else:
            raise TypeError()

        self._current_window = None

    def _open_photo_settings(self):
        self._close_current_window()

        if self._photo_window is None: # TODO: Is there any reason to not have this built, how much memory
            self._photo_window = PhotoSettings(self._main_window, self._settings_container, self._photos_container, self._destroy_photo_window)
        self._photo_window.place(x=self._MENU_WIDTH, y=0, anchor="nw", width=WINDOW_WIDTH-self._MENU_WIDTH, height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT)
        self._current_window = self.OpenWindow.Photo

    def _open_system_settings(self):
        self._close_current_window()

        if self._system_window is None:
            self._system_window = SystemSettings(self._main_window)
        self._system_window.place(x=self._MENU_WIDTH, y=0, anchor="nw", width=WINDOW_WIDTH-self._MENU_WIDTH, height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT)
        self._current_window = self.OpenWindow.System

    def _open_display_settings(self):
        self._close_current_window()

        if self._display_window is None:
            self._display_window = DisplaySettings(self._main_window)
        self._display_window.place(x=self._MENU_WIDTH, y=0, anchor="nw", width=WINDOW_WIDTH-self._MENU_WIDTH, height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT)
        self._current_window = self.OpenWindow.Display

    def place(self, **place_kwargs):
        self._main_window.place(**place_kwargs)
        self._menu.reset()

    def place_forget(self):
        self._main_window.place_forget()
        self._menu.reset()
