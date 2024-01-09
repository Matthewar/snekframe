"""Main Windows"""

import logging # TODO: Update logging to include filename
import os
import os.path
import sys

import tkinter as tk
import tkinter.ttk as ttk

from . import db, styles
from .fonts import FONTS
from .styles import STYLES
from .params import WINDOW_WIDTH, WINDOW_HEIGHT, FILES_LOCATION, PHOTOS_LOCATION, DATABASE_NAME
from .photowindow import PhotoWindow

class EntryWindow:
    """Startup settings"""
    def __init__(self, frame, exit_window_callback):
        self._window = frame

        title_label = ttk.Label(self._window, text="Hello!", font=FONTS.title)
        subtitle_label = ttk.Label(self._window, text="Press 'Start' to create database and startup system", font=FONTS.subtitle)
        info_label = ttk.Label(self._window, text="This will reset and create a new database.\nIf not expecting to see this message, please contact your local Matt", justify=tk.LEFT, font=FONTS.default)
        basic_settings_button = ttk.Button(self._window, text="Start", command=exit_window_callback) # font

        # TODO: Add warning symbol

        elements = (title_label, subtitle_label, info_label, basic_settings_button)

        for row, element in enumerate(elements, start=1):
            element.grid(column=1, row=row, pady=10)

        self._window.grid_columnconfigure(0, weight=1)
        self._window.grid_columnconfigure(2, weight=1)
        self._window.grid_rowconfigure(0, weight=1)
        self._window.grid_rowconfigure(len(elements) + 1, weight=1)

        logging.info("Generated entry window")

    def place(self, **place_args):
        """Place window in parent"""
        self._window.place(**place_args)

    def place_forget(self):
        """Remove window"""
        self._window.place_forget()

class VersionWindow:
    def __init__(self, frame, current_major, current_minor, exit_window_callback):
        self._window = frame
        self._exit_window_callback = exit_window_callback

        title_label = ttk.Label(master=self._window, text="Version Change Detected", font=FONTS.title)

        current_version = (current_major, current_minor)
        program_version = (db.DATABASE_VERSION_MAJOR, db.DATABASE_VERSION_MINOR)

        if program_version < current_version:
            info_text = "Database version is newer than installed program."
            upgrade_button = False
            continue_button = False
        elif db.DATABASE_VERSION_MAJOR > current_major:
            info_text = "Database requires updating in order to continue."
            upgrade_button = True
            continue_button = False
        elif db.DATABASE_VERSION_MINOR > current_minor:
            info_text = "New database version detected, upgrade recommended."
            upgrade_button = True
            continue_button = True
        else:
            raise Exception("Shouldn't hit this")

        subtitle_label = ttk.Label(master=self._window, text=info_text, fonts=FONTS.subtitle, justify=tk.CENTER)
        info_label = ttk.Label(master=self._window, text=f"Current Version: {current_major}.{current_minor} - New Version: {db.DATABASE_VERSION_MAJOR}.{db.DATABASE_VERSION_MINOR}", fonts=FONTS.default, justify=tk.CENTER)

        elements = [title_label, subtitle_label, info_label]

        if upgrade_button:
            elements.append(ttk.Button(master=self._window, text="Upgrade", command=self._trigger_upgrade))
        if continue_button:
            elements.append(ttk.Button(master=self._window, text="Continue (without upgrading)", command=exit_window_callback))

    def _trigger_upgrade(self):
        raise NotImplementedError("Currently on version v0.0, no reason to upgrade")

    def place(self, **place_args):
        """Place window in parent"""
        self._window.place(**place_args)

    def place_forget(self):
        """Remove window"""
        self._window.place_forget()

class MainWindow:
    """Holds all other windows"""
    def __init__(self):
        self._root = tk.Tk()
        self._root.title("Photos")
        self._root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self._root.resizable(False, False)
        self._root.attributes("-fullscreen", True)
        self._root.configure(background=styles.DEFAULT_BACKGROUND_COLOUR)

        FONTS.generate()
        STYLES.generate()

        self._windows = {}
        self._generate_windows()

    def _generate_photo_window(self):
        self._windows["photos"] = PhotoWindow(ttk.Frame(master=self._root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT))
        self._windows["photos"].place(x=0, y=0, anchor="nw")

    def _generate_windows(self):
        """Generate all the potential windows"""
        # Whether to generate the initial setup page
        if not os.path.exists(os.path.join(FILES_LOCATION, DATABASE_NAME)):
            #ttk.Style().configure("Test.TFrame", background="green")
            self._windows["entrypoint"] = EntryWindow(ttk.Frame(master=self._root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT), self._close_entrypoint)
            #self._windows["entrypoint"] = EntryWindow(ttk.Frame(master=self._root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, style="Test.TFrame"), self._close_entrypoint)
            self._windows["entrypoint"].place(x=0, y=0, anchor="nw", width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        else:
            database_major, database_minor = db.get_database_version()
            if database_major != db.DATABASE_VERSION_MAJOR or database_minor != db.DATABASE_VERSION_MINOR:
                self._windows["upgrade_version"] = VersionWindow(ttk.Frame(master=self._root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT), database_major, database_minor, self._close_upgrade_window)
                self._windows["upgrade_version"].place(x=0, y=0, anchor="nw", width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
            else:
                self._generate_photo_window()

    def _close_entrypoint(self):
        if "entrypoint" not in self._windows:
            logging.error("Tried to close entrypoint window when it didn't exist")
            return

        # Generate persistent database
        os.makedirs(FILES_LOCATION, exist_ok=True)
        try:
            os.mkdir(os.path.join(FILES_LOCATION, PHOTOS_LOCATION))
        except FileExistsError:
            pass
        db.PersistentBase.metadata.create_all(db.PERSISTENT_ENGINE)
        db.SharedBase.metadata.create_all(db.PERSISTENT_ENGINE)
        with db.PERSISTENT_SESSION() as session:
            # TODO: Add defaults to ORM?
            session.add(db.DatabaseVersion())
            session.add(db.CurrentDisplay(all_photos=False, album=None))
            session.add(db.Settings())
            session.commit()

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
