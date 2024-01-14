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

from .analyse import load_photo_files, setup_viewed_photos
from .db import Settings, PhotoList, RUNTIME_SESSION, PERSISTENT_SESSION, RUNTIME_ENGINE, NumPhotos, get_database_version
from .fonts import FONTS
from . import params
from . import icons
from . import elements
from .params import WINDOW_WIDTH, WINDOW_HEIGHT, TITLE_BAR_HEIGHT
from . import styles

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

class SettingsMenu(elements.LimitedFrameBaseElement):
    """Sidebar menu for various settings pages"""
    def __init__(self, parent, open_photo_settings, open_system_settings):
        super().__init__(parent, {})

        menu_buttons = elements.RadioButtonSet(default_button_cls=elements.IconTextRadioButton)

        self._photo_settings_button = menu_buttons.add_button(self._frame, open_photo_settings, text="Photos", icon_name="photo", selected=False)
        self._photo_settings_button.grid(row=0, column=0)

        system_settings_button = menu_buttons.add_button(self._frame, open_system_settings, text="System", icon_name="computer", selected=False)
        system_settings_button.grid(row=1, column=0)

        self._frame.grid_rowconfigure(2, weight=1)

    def reset(self):
        """Bring to default viewstate"""
        self._photo_settings_button.invoke()

    def winfo_reqwidth(self):
        """Call the winfo_reqwidth of the underlying frame"""
        return self._frame.winfo_reqwidth()

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

        shuffle_off_button = shuffle_buttons.add_button(self._frame, unshuffle_photos, selected=False, text="Off")
        shuffle_off_button.grid(row=0, column=1)

        def shuffle_photos():
            settings_container.shuffle_photos = True
            reshuffle_button.enabled = True
            reshuffle_button.invoke()

        shuffle_on_button = shuffle_buttons.add_button(self._frame, shuffle_photos, selected=False, text="On")
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
        self._decrease_time_button.place(relx=0.3, rely=0.5, anchor=tk.CENTER)

        self._time_info = elements.UpdateLabel(self._frame, initialtext=self._get_transition_time_string())
        self._time_info.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._increase_time_button = elements.IconButton(self._frame, self._increase_time, "plus", enabled=self._can_increase_time())
        self._increase_time_button.place(relx=0.6, rely=0.5, anchor=tk.CENTER)

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

        if position == 0:
            self._decrease_time_button.enabled = False
        self._increase_time_button.enabled = True

    def _increase_time(self):
        position = bisect.bisect_right(self._TRANSITION_TIMES, self._settings_container.photo_change_time)
        if position < len(self._TRANSITION_TIMES):
            self._settings_container.photo_change_time = self._TRANSITION_TIMES[position]
            self._time_info.text = self._get_transition_time_string()

        if self._can_increase_time():
            self._increase_time_button.enabled = False
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
    def __init__(self, parent, settings_container, photo_selection, destroy_photo_window):
        super().__init__(parent, {})

        self._settings_container = settings_container
        self._photo_selection = photo_selection
        self._destroy_photo_window = destroy_photo_window

        row = 1
        LEFTCOLUMN = 1
        RIGHTCOLUMN = LEFTCOLUMN + 1

        shuffle_photos_label = ttk.Label(self._frame, text="Shuffle:", justify=tk.LEFT, font=FONTS.default)
        shuffle_photos_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        shuffle_photos_settings = PhotoShuffleSettings(self._frame, settings_container, self._reorder_photos, destroy_photo_window)
        shuffle_photos_settings.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        photo_transition_label = ttk.Label(self._frame, text="Photo Transition Time", justify=tk.LEFT, font=FONTS.default)
        photo_transition_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        photo_transition_controls = PhotoTransitionSettings(self._frame, settings_container)
        photo_transition_controls.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        photos_info_label = ttk.Label(self._frame, text="Number of Photos:", justify=tk.LEFT, font=FONTS.default)
        photos_info_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        self._num_photos_label = elements.UpdateLabel(self._frame, initialtext="Loading", justify=tk.RIGHT, font=FONTS.default)
        self._num_photos_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        albums_info_label = ttk.Label(self._frame, text="Number of Albums:", justify=tk.LEFT, font=FONTS.default)
        albums_info_label.grid(row=row, column=LEFTCOLUMN, pady=5)
        self._num_albums_label = elements.UpdateLabel(self._frame, initialtext="Loading", justify=tk.RIGHT, font=FONTS.default)
        self._num_albums_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        self._update_num_photo_labels()

        row += 1

        rescan_photos_label = ttk.Label(self._frame, text="Rescan:", justify=tk.LEFT, font=FONTS.default)
        rescan_photos_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        rescan_photos_button = elements.TextButton(self._frame, self._trigger_rescan, text="Go!")
        rescan_photos_button.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_columnconfigure(RIGHTCOLUMN+1, weight=1)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(row, weight=1)

    def _reorder_photos(self):
        """Reorder existing list of photos

        According to shuffle setting and photo selection
        Returns whether any photos are available
        """
        if self._photo_selection.album_selected:
            album = self._photo_selection.album
        elif self._photo_selection.all_photos_selected:
            album = None
        else:
            # No photos selected
            return False

        return setup_viewed_photos(shuffle=self._settings_container.shuffle_photos, album=album)

    def _update_num_photo_labels(self):
        """Update the labels with number of photos"""
        with RUNTIME_SESSION() as session:
            result = session.scalars(
                select(NumPhotos).limit(1)
            ).one_or_none()

            if result is None:
                # TODO: Log error
                self._num_photos_label.text = "Error!"
                self._num_albums_label.text = "Error!"
            else:
                self._num_photos_label.text = str(result.num_photos)
                self._num_albums_label.text = str(result.num_albums)

    def _trigger_rescan(self):
        """Rescan directory for photos"""
        # TODO: Add threading? Need to block moving off this screen if so
        load_photo_files()
        found_photos = self._reorder_photos()
        if not found_photos:
            self._photo_selection.set_no_selection()
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
        self._button.place(relx=0.3, rely=0.5, anchor="e")

        self._label = elements.UpdateLabel(self._frame, initialtext="")
        self._label.place(relx=0.4, rely=0.5, anchor="w")

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
        else:
            self._system_call()

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
        subprocess.run(["sudo", "/sbin/shutdown", "now"])

class _RestartCallWindow(_SystemCallWindow):
    def __init__(self, parent):
        super().__init__(parent, "Restart", "Restarting")

    def _system_call(self):
        subprocess.run(["sudo", "/sbin/reboot"])

class SystemSettings(elements.LimitedFrameBaseElement):
    def __init__(self, parent):
        super().__init__(parent, {})

        row = 1
        LEFTCOLUMN = 1
        RIGHTCOLUMN = LEFTCOLUMN + 1
        COLUMNSPAN = RIGHTCOLUMN - LEFTCOLUMN + 1

        ip_addr_title_label = ttk.Label(self._frame, text="IP Address:", justify=tk.LEFT, font=FONTS.default)
        ip_addr_title_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        self._ip_addr_info_label = AutoUpdateIPLabel(self._frame, justify=tk.RIGHT, font=FONTS.default) # TODO: Add loading initial text?
        self._ip_addr_info_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        self._shutdown_window = _ShutdownCallWindow(self._frame)
        self._shutdown_window.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN)

        row += 1

        self._restart_window = _RestartCallWindow(self._frame)
        self._restart_window.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN)

        row += 1

        current_db_version_label = ttk.Label(self._frame, text="Current Database Version:", justify=tk.LEFT, font=FONTS.default)
        current_db_version_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        db_version_label = ttk.Label(self._frame, text="v{:d}.{:d}".format(*get_database_version()), justify=tk.RIGHT, font=FONTS.default)
        db_version_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        current_version_string = importlib.metadata.version("snekframe")
        self._current_version = tuple(current_version_string.split('.'))

        current_version_label = ttk.Label(self._frame, text="Current Version:", justify=tk.LEFT, font=FONTS.default)
        current_version_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        version_label = ttk.Label(self._frame, text=current_version_string, justify=tk.RIGHT, font=FONTS.default)
        version_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        upgrade_label = ttk.Label(self._frame, text="Upgrade Available:", justify=tk.LEFT, font=FONTS.default)
        upgrade_label.grid(row=row, column=LEFTCOLUMN, pady=5)

        self._upgrade_info_label = elements.UpdateLabel(self._frame)
        self._upgrade_info_label.grid(row=row, column=RIGHTCOLUMN, pady=5)

        row += 1

        self._upgrade_info_text = None
        self._upgrade_available = None # Version available
        self._upgrade_check_thread = None

        self._upgrade_button = elements.TextButton(self._frame, text="Upgrade", enabled=False, command=self._run_upgrade)
        self._upgrade_button.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN)

        row += 1

        self._check_upgrade_button = elements.TextButton(self._frame, text="Check for upgrade", command=self._check_upgrade)
        self._check_upgrade_button.grid(row=row, column=LEFTCOLUMN, columnspan=COLUMNSPAN)
        self._check_upgrade_button.invoke()
        self._check_upgrade()

        row += 1

        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_columnconfigure(RIGHTCOLUMN+1, weight=1)
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

class SettingsWindow:
    class OpenWindow(Enum):
        Photo = auto()
        System = auto()

    def __init__(self, parent, selection, settings, destroy_photo_window): # TODO: Previous screen if possible
        self._main_window = ttk.Frame(master=parent)

        self._menu = SettingsMenu(self._main_window, self._open_photo_settings, self._open_system_settings)
        self._menu.place(x=0, y=0, anchor="nw", height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT)
        self._current_window = None

        self._photo_selection = selection
        self._settings_container = settings
        self._destroy_photo_window = destroy_photo_window

        self._photo_window = PhotoSettings(self._main_window, self._settings_container, self._photo_selection, self._destroy_photo_window)
        self._system_window = SystemSettings(self._main_window)

    def _close_current_window(self):
        if self._current_window is None:
            return # Skip, should only occur on startup
        if self._current_window == self.OpenWindow.Photo:
            self._photo_window.place_forget()
        elif self._current_window == self.OpenWindow.System:
            self._system_window.place_forget()
        else:
            raise TypeError()

        self._current_window = None

    def _open_photo_settings(self):
        self._close_current_window()

        if self._photo_window is None: # TODO: Is there any reason to not have this built, how much memory
            self._photo_window = PhotoSettings(self._main_window, self._settings_container, self._photo_selection, self._destroy_photo_window)
        self._photo_window.place(x=self._menu.winfo_reqwidth(), y=TITLE_BAR_HEIGHT, anchor="nw", width=WINDOW_WIDTH-self._menu.winfo_reqwidth())
        self._current_window = self.OpenWindow.Photo

    def _open_system_settings(self):
        self._close_current_window()

        if self._system_window is None:
            self._system_window = SystemSettings(self._main_window)
        self._system_window.place(x=self._menu.winfo_reqwidth(), y=TITLE_BAR_HEIGHT, anchor="nw", width=WINDOW_WIDTH-self._menu.winfo_reqwidth())
        self._current_window = self.OpenWindow.System

    def place(self, **place_kwargs):
        self._main_window.place(**place_kwargs)
        self._menu.reset()

    def place_forget(self):
        self._main_window.place_forget()
        self._close_current_window()
