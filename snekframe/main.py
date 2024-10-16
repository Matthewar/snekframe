"""Main Windows"""

import logging # TODO: Update logging to include filename
import os
import os.path
import sys

import tkinter as tk
from tkinter import ttk

from . import db, styles, params, elements
from .fonts import FONTS
from .styles import STYLES
from .photos.main import PhotoWindow

class EntryWindow(elements.LimitedFrameBaseElement):
    """Startup settings"""
    def __init__(self, parent, exit_window_callback):
        super().__init__(parent, {})

        title_label = ttk.Label(self._frame, text="Hello!", font=FONTS.title)
        subtitle_label = ttk.Label(self._frame, text="Press 'Start' to create database and startup system", font=FONTS.subtitle)
        info_label = ttk.Label(self._frame, text="This will reset and create a new database.\nIf not expecting to see this message, please contact your local Matt", justify=tk.LEFT, font=FONTS.default)
        basic_settings_button = elements.TextButton(self._frame, text="Start", command=exit_window_callback) # font

        # TODO: Add warning symbol

        rows = (title_label, subtitle_label, info_label, basic_settings_button)

        for row, element in enumerate(rows, start=1):
            element.grid(column=1, row=row, pady=10)

        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_columnconfigure(2, weight=1)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(len(rows) + 1, weight=1)

        logging.info("Generated entry window")

class VersionWindow(elements.LimitedFrameBaseElement):
    def __init__(self, parent, current_major, current_minor, exit_window_callback):
        super().__init__(parent, {})

        self._exit_window_callback = exit_window_callback

        title_label = ttk.Label(master=self._frame, text="Version Change Detected", font=FONTS.title)

        current_version = (current_major, current_minor)
        program_version = (db.version.DATABASE_VERSION_MAJOR, db.version.DATABASE_VERSION_MINOR)

        if program_version < current_version:
            info_text = "Database version is newer than installed program."
            upgrade_button = False
            continue_button = False
        elif db.version.DATABASE_VERSION_MAJOR > current_major:
            info_text = "Database requires updating in order to continue."
            upgrade_button = True
            continue_button = False
        elif db.version.DATABASE_VERSION_MINOR > current_minor:
            info_text = "New database version detected, upgrade recommended."
            upgrade_button = True
            continue_button = True
        else:
            raise Exception("Shouldn't hit this")

        subtitle_label = ttk.Label(master=self._frame, text=info_text, font=FONTS.subtitle, justify=tk.CENTER)
        info_label = ttk.Label(
            master=self._frame,
            text=f"Current Version: {current_major}.{current_minor} - New Version: {db.version.DATABASE_VERSION_MAJOR}.{db.version.DATABASE_VERSION_MINOR}",
            font=FONTS.default,
            justify=tk.CENTER
        )

        rows = [title_label, subtitle_label, info_label]

        if upgrade_button:
            rows.append(elements.TextButton(self._frame, command=self._trigger_upgrade, text="Upgrade"))
        if continue_button:
            rows.append(elements.TextButton(self._frame, command=exit_window_callback, text="Continue (without upgrading)"))

        for row, element in enumerate(rows, start=1):
            element.grid(column=1, row=row, pady=10)

        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_columnconfigure(2, weight=1)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(len(rows) + 1, weight=1)

    def _trigger_upgrade(self):
        db.upgrade.upgrade_database()
        self._exit_window_callback()

class MainWindow:
    """Holds all other windows"""
    def __init__(self):
        self._root = tk.Tk()
        self._root.title("Photos")
        self._root.geometry(f"{params.WINDOW_WIDTH}x{params.WINDOW_HEIGHT}")
        self._root.resizable(False, False)
        self._root.attributes("-fullscreen", True)
        self._root.configure(background=styles.DEFAULT_BACKGROUND_COLOUR.string)

        FONTS.generate()
        STYLES.generate()

        self._windows = {}
        self._generate_windows()

    def _generate_photo_window(self):
        self._windows["photos"] = PhotoWindow(ttk.Frame(master=self._root, width=params.WINDOW_WIDTH, height=params.WINDOW_HEIGHT))
        self._windows["photos"].place(x=0, y=0, anchor="nw")

    def _generate_windows(self):
        """Generate all the potential windows"""
        # Whether to generate the initial setup page
        if not os.path.exists(os.path.join(params.FILES_LOCATION, params.DATABASE_NAME)):
            self._windows["entrypoint"] = EntryWindow(self._root, self._close_entrypoint)
            self._windows["entrypoint"].place(x=0, y=0, anchor="nw", width=params.WINDOW_WIDTH, height=params.WINDOW_HEIGHT)
        else:
            database_major, database_minor = db.version.get_database_version()
            if database_major != db.version.DATABASE_VERSION_MAJOR or database_minor != db.version.DATABASE_VERSION_MINOR:
                self._windows["upgrade_version"] = VersionWindow(self._root, database_major, database_minor, self._close_upgrade_window)
                self._windows["upgrade_version"].place(x=0, y=0, anchor="nw", width=params.WINDOW_WIDTH, height=params.WINDOW_HEIGHT)
            else:
                self._generate_photo_window()

    def _close_entrypoint(self):
        if "entrypoint" not in self._windows:
            logging.error("Tried to close entrypoint window when it didn't exist")
            return

        # Generate photos directory
        try:
            os.mkdir(os.path.join(params.FILES_LOCATION, params.PHOTOS_LOCATION))
        except FileExistsError:
            pass
        # Generate persistent database
        db.startup.create_database_file()

        self._generate_photo_window()
        self._windows["entrypoint"].place_forget()
        del self._windows["entrypoint"]

    def _close_upgrade_window(self):
        if "upgrade_version" not in self._windows:
            logging.error("Tried to close upgrade window when it didn't exist")
            return

        self._generate_photo_window()
        self._windows["upgrade_version"].place_forget()
        del self._windows["upgrade_version"]

    def launch(self):
        """Start GUI event loop"""
        self._root.mainloop()


def main():
    """Main"""
    return MainWindow().launch()

if __name__ == "__main__":
    sys.exit(main())
