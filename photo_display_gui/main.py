"""Main Windows"""

import logging # TODO: Update logging to include filename
import os
import os.path
import sys

import tkinter as tk
import tkinter.ttk as ttk

from .db import PERSISTENT_ENGINE, PERSISTENT_SESSION, PersistentBase, DatabaseVersion, CurrentDisplay, Settings, SharedBase
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

class MainWindow:
    """Holds all other windows"""
    def __init__(self):
        self._root = tk.Tk()
        self._root.title("Photos")
        self._root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self._root.resizable(False, False)

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
        PersistentBase.metadata.create_all(PERSISTENT_ENGINE)
        SharedBase.metadata.create_all(PERSISTENT_ENGINE)
        with PERSISTENT_SESSION() as session:
            # TODO: Add defaults to ORM?
            session.add(DatabaseVersion(version="0.0.1"))
            session.add(CurrentDisplay(all_photos=False, album=None))
            session.add(Settings(shuffle_photos=False, sleep_start_time=None, sleep_end_time=None, photo_change_time=5))
            session.commit()

        self._generate_photo_window()
        self._windows["entrypoint"].place_forget()
        del self._windows["entrypoint"]

    def launch(self):
        """Start GUI event loop"""
        self._root.mainloop()


def main():
    """Main"""
    return MainWindow().launch()

if __name__ == "__main__":
    sys.exit(main())
