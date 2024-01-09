"""UI Elements"""

import datetime

import tkinter as tk
from tkinter import ttk

class UpdateLabel:
    """Label with text that can be updated"""
    _LABEL_KWARGS = set(("anchor", "justify", "font", "style"))

    def __init__(self, parent, initialtext=None, **label_kwargs):
        for key in label_kwargs:
            if key not in self._LABEL_KWARGS:
                raise TypeError(f"Unexpected kwarg '{key}' not allowed in constructor")

        self._text = tk.StringVar(value=initialtext)
        self._label = ttk.Label(master=parent, textvariable=self._text, **label_kwargs)

    @property
    def text(self):
        """Label text"""
        return self._text.get()

    @text.setter
    def text(self, value):
        self._text.set(value)

    def place(self, **place_kwargs):
        """Place label in parent"""
        self._label.place(**place_kwargs)

    def place_forget(self):
        """Remove label from parent"""
        self._label.place_forget()

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
