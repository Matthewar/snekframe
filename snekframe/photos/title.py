"""Main Title Bar Related Elements"""

import subprocess

import tkinter as tk
from tkinter import ttk

from .. import elements
from ..fonts import FONTS
from ..params import WINDOW_WIDTH, TITLE_BAR_HEIGHT

class _VoltageWarningIconRadioButton(elements.IconRadioButton):
    _REFRESH_TIME = 30 * 60 * 1000 # 30 minutes

    def __init__(self, parent, open_warning_callback, show_warning_callback=None, hide_warning_callback=None, close_warning_callback=None, enabled=False, selected=False, style="Voltage", **radio_kwargs):
        if show_warning_callback is None or hide_warning_callback is None or close_warning_callback is None:
            raise TypeError()

        self._show_warning = show_warning_callback
        self._hide_warning = hide_warning_callback
        self._close_warning = close_warning_callback

        super().__init__(parent, open_warning_callback, icon_name="bolt", enabled=enabled, selected=selected, style=style, **radio_kwargs)
        self._element.after(1000, self._update_state) # Wait for construction to finish before trying to update the state

    def _set_enable(self, enable):
        super()._set_enable(enable)
        if not self._enabled:
            self._hide_warning()
        else:
            self._show_warning()

    def _update_state(self):
        check_throttled = subprocess.run(["vcgencmd", "get_throttled"], check=True, text=True, stdout=subprocess.PIPE)
        throttled_value = int(check_throttled.stdout.rstrip('\n')[len("throttled="):], 16)

        under_voltage = bool(throttled_value & 0x1)
        if under_voltage:
            if self._selected or self._enabled:
                # Do nothing, currently displaying the voltage symbol
                return
            self.enabled = True
            self._show_warning()
        else:
            if self._selected:
                self._hide_warning()
                self._close_warning()
            elif not self._enabled:
                self.enabled = False
                self._hide_warning()

        self._element.after(self._REFRESH_TIME, self._update_state)

class VoltageWarningWindow(elements.LimitedFrameBaseElement):
    def __init__(self, parent):
        super().__init__(parent, {})

        lines = [
            "Low voltage detected!",
            "Power supply may be insufficient, recommended 5V 2.5A supply"
        ]

        info_label = ttk.Label(master=parent, text="\n".join(lines), justify=tk.CENTER)
        info_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

class PhotoTitleBar(elements.LimitedFrameBaseElement):
    """Titlebar for system"""

    def __init__(self, parent, photo_selection, open_slideshow, open_gallery, open_settings, open_voltage_warning):
        super().__init__(parent, {}, style="TitleBar")

        self._title = elements.UpdateLabel(self._frame, justify=tk.CENTER, font=FONTS.title, style="TitleBar")
        self._title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._datetime = elements.AutoUpdateDateLabel(self._frame, justify=tk.RIGHT, font=FONTS.bold, style="TitleBar")
        self._datetime.place(x=WINDOW_WIDTH-15, rely=0.5, anchor="e")

        title_menu = ttk.Frame(master=self._frame, style="TitleBar.TFrame")
        title_menu.place(x=2.5, rely=0.5, anchor="w")
        self._title_menu_buttons = elements.RadioButtonSet(default_button_cls=elements.IconRadioButton, style="Title")

        column = 0

        def callback_open_settings():
            open_settings()
            self._title.text = "Settings"

        self._settings_button = self._title_menu_buttons.add_button(title_menu, callback_open_settings, icon_name="settings", selected=False)
        self._settings_button.grid(row=0, column=column, padx=(15, 5))

        column += 1

        def callback_open_gallery():
            open_gallery()
            self._title.text = "Gallery"

        self._gallery_button = self._title_menu_buttons.add_button(title_menu, callback_open_gallery, icon_name="photo_library", selected=False)
        self._gallery_button.grid(row=0, column=column, padx=5)

        column += 1

        def callback_open_slideshow():
            open_slideshow()
            self._title.text = "Slideshow" # TODO: Change to selected photo name

        self._slideshow_button = self._title_menu_buttons.add_button(title_menu, callback_open_slideshow, icon_name="slideshow", selected=False, enabled=photo_selection.photos_selected)
        self._slideshow_button.grid(row=0, column=column, padx=5)

        column += 1

        def callback_open_voltage():
            open_voltage_warning()
            self._title.text = "Low Voltage"

        self._voltage_button = self._title_menu_buttons.add_button(title_menu, callback_open_voltage, button_cls=_VoltageWarningIconRadioButton, selected=False, enabled=False, show_warning_callback=self._show_voltage_warning, hide_warning_callback=self._hide_voltage_warning, close_warning_callback=callback_open_settings, style="Voltage")
        # Setup grid options
        self._voltage_button.grid(row=0, column=column, padx=5)
        self._voltage_button.grid_remove()

        self._visible = False

    def _show_voltage_warning(self):
        self._voltage_button.grid()

    def _hide_voltage_warning(self):
        self._voltage_button.grid_remove()

    @property
    def visible(self):
        """If the title bar is visible"""
        return self._visible

    def place(self, unpause_datetime=True):
        super().place(x=0, y=0, anchor="nw", width=WINDOW_WIDTH, height=TITLE_BAR_HEIGHT) # TODO: Move place_kwargs
        self._frame.tkraise()
        if unpause_datetime:
            self._datetime.update_label()
        self._visible = True

    def place_forget(self, pause_datetime=True):
        super().place_forget()
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

    def invoke_gallery_button(self):
        """Invoke the photo gallery button

        This will trigger updating this class for gallery along with the gallery callback triggers
        """
        self._gallery_button.invoke()
