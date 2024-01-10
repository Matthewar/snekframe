"""UI Elements"""

import datetime

import tkinter as tk
from tkinter import ttk

from .icons import ICONS

class _LimitedLabel:
    """Basic label wrapper with limited parameters

    Defaults to no supported label parameters, not intended for this to be used externally
    """
    _LABEL_KWARGS : set[str] = set()

    def __init__(self, parent, user_label_kwargs, **label_kwargs):
        for key in label_kwargs:
            if key not in self._LABEL_KWARGS:
                raise TypeError(f"Unexpected kwarg '{key}' not allowed in constructor")

        all_kwargs = user_label_kwargs | label_kwargs
        self._label = ttk.Label(master=parent, **all_kwargs)

    def place(self, **place_kwargs):
        """Place label in parent"""
        self._label.place(**place_kwargs)

    def place_forget(self):
        """Remove label from parent"""
        self._label.place_forget()

class UpdateLabel(_LimitedLabel):
    """Label with text that can be updated"""
    _LABEL_KWARGS = set(("anchor", "justify", "font", "style"))

    def __init__(self, parent, initialtext=None, **label_kwargs):
        self._text = tk.StringVar(value=initialtext)
        super().__init__(parent, label_kwargs, textvariable=self._text)

    @property
    def text(self):
        """Label text"""
        return self._text.get()

    @text.setter
    def text(self, value):
        self._text.set(value)

class AutoUpdateLabel(UpdateLabel):
    """Label with text that can be updated

    Label will also update periodically (won't start until placed)
    """

    UPDATE_CALLBACK_MIN_TIME_MS = 1000

    def __init__(self, parent, initialtext=None, **label_kwargs):
        super().__init__(parent, initialtext=initialtext, **label_kwargs)

        self._update_job = None
        if initialtext is None:
            self._update_label()

    def _update_label(self):
        """Update label callback, needs to be overridden"""
        raise NotImplementedError()

    def _update_label_no_cancel(self):
        """This should only be called by the after callback

        IE there won't be an update_job running any more
        """
        self._update_label()
        self._update_job = self._label.after(self.UPDATE_CALLBACK_MIN_TIME_MS, self._update_label_no_cancel)

    def update_label(self):
        """Update the label and unpause updates if paused"""
        self.pause_updates()
        self._update_label_no_cancel()

    def pause_updates(self):
        """Pause auto updating label"""
        if self._update_job is not None:
            self._label.after_cancel(self._update_job)
            self._update_job = None

    @property
    def updates_paused(self):
        """Whether the label is currently updating"""
        return self._update_job is None

    def place(self, unpause_updates=True, **place_kwargs):
        """Place label in parent

        Defaults to start updating the label
        """
        if unpause_updates:
            self.update_label()
        super().place_forget()

    def place_forget(self, pause_updates=True):
        """Remove label from parent

        Defaults to pause updating the label
        """
        if pause_updates:
            self.pause_updates()
        super().place_forget()

class AutoUpdateDateLabel(AutoUpdateLabel):
    """Label with datetime that auto updates"""

    UPDATE_CALLBACK_MIN_TIME_MS = 10000 # Every 30 seconds (only display up to minute)

    def __init__(self, parent, **label_kwargs):
        if "initialtext" in label_kwargs:
            raise TypeError("kwarg 'initialtext' not permitted in {}".format(self.__class__.__name__))
        super().__init__(parent, **label_kwargs)

    def _update_label(self):
        """Update current time display"""
        self.text = datetime.datetime.now().strftime("%a %d/%m/%Y, %I:%M%p")

class _Button(_LimitedLabel):
    """Custom basic button

    - Button 1 -> Switched from normal to active (if not disabled)
    - Leave -> If clicked, goes from active to normal
    - Enter -> If still clicked, goes from normal to active
    - Button Release 1 -> Switches from active to normal. Triggers command
    """
    def __init__(self, parent, command, user_label_kwargs, enabled=True, **label_kwargs):
        super().__init__(parent, user_label_kwargs, **label_kwargs)
        self._setup_bindings(command)

        self._clicked = (False, False)
        self._enabled = enabled

        if not self._enabled:
            self._style_disabled(None)
        else:
            self._style_active(None)

    @property
    def enabled(self):
        """Whether the button is enabled"""
        return self._enabled

    @enabled.setter
    def enabled(self, enable):
        if not isinstance(enable, bool):
            raise TypeError("Button enable is boolean")
        if self._enabled and not enable:
            self._style_disabled(None)
        elif not self._enabled and enable:
            self._style_normal(None)
        self._enabled = enable

    def _setup_bindings(self, command):
        self._label.bind("<Button-1>", self._callback_click)
        self._label.bind("<ButtonRelease-1>", lambda event: self._callback_release(event, command))
        self._label.bind("<Enter>", self._callback_enter)
        self._label.bind("<Leave>", self._callback_leave)

    def _callback_click(self, event):
        if not self._enabled:
            return

        self._style_active(event)
        self._clicked = (True, True)

    def _callback_enter(self, event):
        if not self._clicked[0]:
            return

        if not self._clicked[1]:
            self._style_active(event)
        self._clicked = (True, True)

    def _callback_leave(self, event):
        if not self._clicked[0]:
            return

        if self._clicked[1]:
            self._style_normal(event)
        self._clicked = (True, False)

    def _callback_release(self, event, command):
        if not self._clicked[0]:
            return
        if self._clicked[1]:
            self._style_normal(event)
            command()
        self._clicked = (False, False)

    def _style_normal(self, event):
        raise NotImplementedError()

    def _style_active(self, event):
        raise NotImplementedError()

    def _style_disabled(self, event):
        raise NotImplementedError()

class IconButton(_Button):
    """Button using image icon"""
    _NORMAL_ICON_COLOUR = "#000000"
    _ACTIVE_ICON_COLOUR = "#ffffff"
    _DISABLED_ICON_COLOUR = "#ABB0B8"

    def __init__(self, parent, command, icon_name, enabled=True, **label_kwargs):
        self._normal_icon = ICONS.get(icon_name, hexcolour=self._NORMAL_ICON_COLOUR)
        self._active_icon = ICONS.get(icon_name, hexcolour=self._ACTIVE_ICON_COLOUR)
        self._disabled_icon = ICONS.get(icon_name, hexcolour=self._DISABLED_ICON_COLOUR)

        super().__init__(parent, command, label_kwargs, enabled=enabled, image=self._normal_icon)

    def _style_normal(self, event):
        self._label.configure(image=self._normal_icon)
        self._label.image = self._normal_icon

    def _style_active(self, event):
        self._label.configure(image=self._active_icon)
        self._label.image = self._active_icon

    def _style_disabled(self, event):
        self._label.configure(image=self._disabled_icon)
        self._label.image = self._disabled_icon
