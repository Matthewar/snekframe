"""UI Elements"""

import collections
import datetime

import tkinter as tk
from tkinter import ttk

from .icons import ICONS
from . import styles

class _LimitedElement:
    """Basic element wrapper with limited parameters

    Defaults to no supported element parameters, not intended for this to be used externally

    Element requires methods:
    - place
    - place_forget
    - grid
    - grid_remove
    """
    _ELEMENT_KWARGS : set[str] = set()

    def __init__(self, parent, element_cls, user_element_kwargs, **element_kwargs):
        for key in user_element_kwargs:
            if key not in self._ELEMENT_KWARGS:
                raise TypeError(f"Unexpected kwarg '{key}' not allowed in {self.__class__.__name__}")

        all_kwargs = user_element_kwargs | element_kwargs
        self._element = element_cls(master=parent, **all_kwargs)

    def place(self, **place_kwargs):
        """Place element in parent"""
        self._element.place(**place_kwargs)

    def place_forget(self):
        """Remove element from parent"""
        self._element.place_forget()

    def grid(self, **grid_kwargs):
        """Grid element into parent"""
        self._element.grid(**grid_kwargs)

    def grid_remove(self):
        """Ungrid element from parent"""
        self._element.grid_remove()

class _LimitedLabel(_LimitedElement):
    """Basic label wrapper with limited parameters

    Defaults to no supported label parameters, not intended for this to be used externally
    """
    def __init__(self, parent, user_label_kwargs, **label_kwargs):
        super().__init__(parent, ttk.Label, user_label_kwargs, **label_kwargs)

    @property
    def _label(self):
        return self._element

class LimitedFrameBaseElement(_LimitedElement):
    """Basic element to build from with a frame

    Defaults to no supported frame parameters, intended to only be used as a parent
    """
    def __init__(self, parent, user_frame_kwargs, **frame_kwargs):
        super().__init__(parent, ttk.Frame, user_frame_kwargs, **frame_kwargs)

    @property
    def _frame(self):
        return self._element

class UpdateLabel(_LimitedLabel):
    """Label with text that can be updated"""
    _LABEL_KWARGS = set(("anchor", "justify", "font", "style"))

    def __init__(self, parent, initialtext=None, variabletype=tk.StringVar, **label_kwargs):
        self._text = variabletype(value=initialtext)
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
        super().place(**place_kwargs)

    def place_forget(self, pause_updates=True):
        """Remove label from parent

        Defaults to pause updating the label
        """
        if pause_updates:
            self.pause_updates()
        super().place_forget()

    def grid(self, unpause_updates=True, **grid_kwargs):
        """Add label to parent grid

        Defaults to start updating the label
        """
        if unpause_updates:
            self.update_label()
        super().grid(**grid_kwargs)

    def grid_remove(self, pause_updates=True):
        """Remove label from parent

        Defaults to pause updating the label
        """
        if pause_updates:
            self.pause_updates()
        super().grid_remove()

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

class _Button(_LimitedElement):
    """Custom basic button

    - Button 1 -> Switched from normal to active (if not disabled)
    - Leave -> If clicked, goes from active to normal
    - Enter -> If still clicked, goes from normal to active
    - Button Release 1 -> Switches from active to normal. Triggers command

    Element additionally requires methods:
    - bind
    """
    def __init__(self, parent, element_cls, command, user_element_kwargs, enabled=True, **element_kwargs):
        super().__init__(parent, element_cls, user_element_kwargs, **element_kwargs)
        self._setup_bindings()

        self._clicked = (False, False)
        self._enabled = enabled
        self._command = command

        if not self._enabled:
            self._style_disabled()
        else:
            self._style_normal()

    @property
    def enabled(self):
        """Whether the button is enabled"""
        return self._enabled

    @enabled.setter
    def enabled(self, enable):
        self._set_enable(enable)

    def _set_enable(self, enable):
        if not isinstance(enable, bool):
            raise TypeError("Button enable is boolean")
        if self._enabled and not enable:
            self._style_disabled()
        elif not self._enabled and enable:
            self._style_normal()
        self._enabled = enable

    def invoke(self):
        """Click Button"""
        if not self._enabled:
            return
        self._style_normal()
        self._command()

    def _setup_bindings(self):
        self._element.bind("<Button-1>", self._callback_click)
        self._element.bind("<ButtonRelease-1>", self._callback_release)
        self._element.bind("<Enter>", self._callback_enter)
        self._element.bind("<Leave>", self._callback_leave)

    def _callback_click(self, event):
        if not self._enabled:
            return

        self._style_active()
        self._clicked = (True, True)

    def _callback_enter(self, event):
        if not self._clicked[0]:
            return

        if not self._clicked[1]:
            self._style_active()
        self._clicked = (True, True)

    def _callback_leave(self, event):
        if not self._clicked[0]:
            return

        if self._clicked[1]:
            self._style_normal()
        self._clicked = (True, False)

    def _callback_release(self, event):
        if not self._clicked[0]:
            return

        if self._clicked[1]:
            self.invoke()
        self._clicked = (False, False)

    def _style_normal(self):
        raise NotImplementedError()

    def _style_active(self):
        raise NotImplementedError()

    def _style_disabled(self):
        raise NotImplementedError()

TextColours = collections.namedtuple(
    "TextColours",
    ["normal_background", "active_background", "disabled_background", "selected_background", "normal_font", "selected_font"]
)

DEFAULT_TEXTBUTTON_COLOURS = TextColours(
    normal_background=styles.DEFAULT_BACKGROUND_COLOUR,
    active_background=styles.Colour(0xffffff),
    disabled_background=styles.Colour(0x000000),
    selected_background=styles.Colour(0xffffff),
    normal_font=styles.Colour(0xffffff),
    selected_font=styles.Colour(0x000000)
)

class TextButton(_Button):
    """Regular button using text label

    Colour changing occurs for the background
    """
    def __init__(self, parent, command, text=None, enabled=True, colours=DEFAULT_TEXTBUTTON_COLOURS, **label_kwargs):
        if text is None:
            raise TypeError()
        super().__init__(parent, ttk.Label, command, label_kwargs, enabled=enabled, text=text, background=colours.normal_background.string, foreground=colours.font.string)
        self._colours = colours

    def _style_normal(self):
        self._element.configure(
            background=self._colours.normal_background.string,
            foreground=self._colours.normal_font.string)

    def _style_active(self):
        self._element.configure(
            background=self._colours.active_background.string,
            foreground=self._colours.normal_font.string)

    def _style_disabled(self):
        self._element.configure(
            background=self._colours.disabled_background.string,
            foreground=self._colours.normal_font.string)

IconColours = collections.namedtuple("IconColours", ["normal", "active", "disabled", "selected", "background"])

DEFAULT_ICON_COLOURS = IconColours(
    background=styles.DEFAULT_BACKGROUND_COLOUR,
    normal=styles.HIGHLIGHT_BACKGROUND_COLOUR,
    active=styles.Colour(0xffffff),
    disabled=styles.Colour(0x000000),
    selected=styles.Colour(0xabb0b8)
)
TITLE_ICON_COLOURS = IconColours(
    background=styles.HIGHLIGHT_BACKGROUND_COLOUR,
    normal=styles.Colour(0xabb0b8),
    active=styles.Colour(0xffffff),
    disabled=styles.Colour(0x000000),
    selected=styles.Colour(0xffffff)
)

class IconButton(_Button):
    """Regular button using image icon"""
    def __init__(self, parent, command, icon_name, enabled=True, colours=DEFAULT_ICON_COLOURS, **label_kwargs):
        self._normal_icon = ICONS.get(icon_name, background=colours.background, pathcolour=colours.normal)
        self._active_icon = ICONS.get(icon_name, background=colours.background, pathcolour=colours.active)
        self._disabled_icon = ICONS.get(icon_name, background=colours.background, pathcolour=colours.disabled)

        super().__init__(parent, ttk.Label, command, label_kwargs, enabled=enabled, image=self._normal_icon, background=colours.background.string)

    def _style_normal(self):
        self._element.configure(image=self._normal_icon)
        self._element.image = self._normal_icon

    def _style_active(self):
        self._element.configure(image=self._active_icon)
        self._element.image = self._active_icon

    def _style_disabled(self):
        self._element.configure(image=self._disabled_icon)
        self._element.image = self._disabled_icon

class _RadioButton(_Button):
    """Button that can be selected"""
    def __init__(self, parent, element_cls, command, user_element_kwargs, enabled=True, selected=False, **element_kwargs):
        if selected and not enabled:
            raise AttributeError("Cannot select disabled button")

        self._selected = selected
        super().__init__(parent, element_cls, command, user_element_kwargs, enabled=enabled, **element_kwargs)

    def _style_selected(self):
        raise NotImplementedError()

    def _set_enable(self, enable):
        if not enable and self._selected:
            raise AttributeError("Cannot disable selected button")
        super()._set_enable(enable)

    @property
    def selected(self):
        """Whether the button is selected"""
        return self._selected

    @selected.setter
    def selected(self, select):
        if not isinstance(select, bool):
            raise TypeError("Button select is boolean")
        if self._selected and not select:
            self._style_normal()
        elif not self._selected and select:
            if self._enabled:
                self._style_selected()
            else:
                raise AttributeError("Cannot select disabled button")
        self._selected = select

    def invoke(self):
        if not self._enabled or self._selected:
            # Don't trigger if already selected (or disabled)
            return
        self._style_selected()
        self._command()

    def _callback_leave(self, event):
        if not self._clicked[0]:
            return

        if self._clicked[1]:
            if self._selected:
                self._style_selected()
            else:
                self._style_normal()
        self._clicked = (True, False)

class TextRadioButton(_RadioButton):
    """RadioButton using text label

    Colour changing occurs for the background
    """
    _LABEL_KWARGS = set(("anchor", "justify", "font"))

    def __init__(self, parent, command, text=None, enabled=True, selected=True, colours=DEFAULT_TEXTBUTTON_COLOURS, **label_kwargs):
        if text is None:
            raise TypeError()
        super().__init__(parent, ttk.Label, command, label_kwargs, enabled=enabled, selected=selected, text=text, background=colours.normal_background.string, foreground=colours.font.string)
        self._colours = colours

    def _style_normal(self):
        self._element.configure(
            background=self._colours.normal_background.string,
            foreground=self._colours.normal_font.string)

    def _style_active(self):
        self._element.configure(
            background=self._colours.active_background.string,
            foreground=self._colours.normal_font.string)

    def _style_disabled(self):
        self._element.configure(
            background=self._colours.disabled_background.string,
            foreground=self._colours.normal_font.string)

    def _style_selected(self):
        self._element.configure(
            background=self._colours.selected_background.string,
            foreground=self._colours.selected_font.string)

class IconRadioButton(_RadioButton):
    """RadioButton using image icon

    Colour changing occurs for the icon
    """
    def __init__(self, parent, command, icon_name=None, enabled=True, selected=True, colours=DEFAULT_ICON_COLOURS, **label_kwargs):
        if icon_name is None:
            raise TypeError()
        self._normal_icon = ICONS.get(icon_name, background=colours.background, pathcolour=colours.normal)
        self._active_icon = ICONS.get(icon_name, background=colours.background, pathcolour=colours.active)
        self._disabled_icon = ICONS.get(icon_name, background=colours.background, pathcolour=colours.disabled)
        self._selected_icon = ICONS.get(icon_name, background=colours.background, pathcolour=colours.selected)

        super().__init__(parent, ttk.Label, command, label_kwargs, enabled=enabled, selected=selected, image=self._normal_icon, background=colours.background.string)

    def _style_normal(self):
        self._element.configure(image=self._normal_icon)
        self._element.image = self._normal_icon

    def _style_active(self):
        self._element.configure(image=self._active_icon)
        self._element.image = self._active_icon

    def _style_disabled(self):
        self._element.configure(image=self._disabled_icon)
        self._element.image = self._disabled_icon

    def _style_selected(self):
        self._element.configure(image=self._selected_icon)
        self._element.image = self._selected_icon

class IconTextRadioButton(_RadioButton):
    """RadioButton with icon and image

    Colour changing affects the background of the icon and text
    """
    def __init__(self, parent, command, text=None, icon_name=None, enabled=True, selected=True, colours=DEFAULT_ICON_COLOURS):
        if text is None or icon_name is None:
            raise TypeError()
        super().__init__(parent, ttk.Frame, command, {}, enabled=enabled, selected=selected, background=colours.background.string)

        self._colours = colours

        icon_image = ICONS.get(icon_name, background=colours.background, pathcolour=colours.normal)
        self._icon = ttk.Label(master=self._element, image=icon_image, background=colours.background.string)
        self._text = ttk.Label(master=self._element, text=text, background=colours.background.string, foreground="white") # TODO Colour
        self._icon.grid(row=0, column=0, padx=(5.0, 2.5))
        self._text.grid(row=0, column=1, padx=(2.5, 5.0))

    def _style_normal(self):
        normal_background = self._colours.background.string

        self._element.configure(background=normal_background)
        self._icon.configure(background=normal_background)
        self._text.configure(background=normal_background)

    def _style_active(self):
        active_background = self._colours.active.string

        self._element.configure(background=active_background)
        self._icon.configure(background=active_background)
        self._text.configure(background=active_background)

    def _style_disabled(self):
        disabled_background = self._colours.disabled.string

        self._element.configure(background=disabled_background)
        self._icon.configure(background=disabled_background)
        self._text.configure(background=disabled_background)

    def _style_selected(self):
        return self._style_active()

class RadioButtonSet:
    def __init__(self, default_button_cls=IconRadioButton, **default_radio_kwargs):
        self._default_button_cls = default_button_cls
        self._default_radio_kwargs = default_radio_kwargs
        self._buttons = {}
        self._next_id = 0
        self._selected = None

    def add_button(self, parent, command, enabled=True, selected=False, button_cls=None, **radio_kwargs):
        if selected and self._selected is not None:
            raise AttributeError("Can only have one selected button")
        if button_cls is None:
            button_cls = self._default_button_cls

        button_id = self._next_id
        self._next_id += 1

        def _update_buttons():
            if self._selected is not None:
                self._buttons[self._selected].selected = False
            self._selected = button_id
            self._buttons[button_id].selected = True
            command()

        button_kwargs = self._default_radio_kwargs.copy()
        button_kwargs.update(radio_kwargs)

        self._buttons[button_id] = button_cls(parent, _update_buttons, enabled=enabled, selected=selected, **button_kwargs)
        if selected:
            self._selected = button_id

        return self._buttons[button_id]

    def deselect_all(self):
        if self._selected is not None:
            self._buttons[self._selected].selected = False
            self._selected = None

class _ToggleButton(_RadioButton):
    def __init__(self, parent, element_cls, select_command, unselect_command, user_element_kwargs, enabled=True, selected=False, **element_kwargs):
        super().__init__(parent, element_cls, select_command, user_element_kwargs, enabled=enabled, selected=selected, **element_kwargs)
        self._unselect_command = unselect_command

    def invoke(self):
        if not self._enabled:
            # Don't trigger is already selected
            return

        if not self._selected:
            self._unselect_command()
            self._style_normal()
        else:
            self._command()
            self._style_selected()

class TextToggleButton(_ToggleButton):
    def __init__(self, parent, select_command, unselect_command, text=None, selected_text=None, enabled=True, selected=False, colours=DEFAULT_TEXTBUTTON_COLOURS, **label_kwargs):
        if text is None:
            raise TypeError()
        self._unselected_text = text
        if selected_text is not None:
            self._selected_text = text

        if selected:
            initialtext = self._selected_text
        else:
            initialtext = self._unselected_text

        super().__init__(parent, ttk.Label, select_command, unselect_command, label_kwargs, enabled=enabled, selected=selected, text=initialtext, background=colours.normal_background.string, foreground=colours.font.string)

        self._colours = colours

    def _style_normal(self):
        self._element.configure(
            background=self._colours.normal_background.string,
            foreground=self._colours.normal_font.string,
            text=self._unselected_text)

    def _style_active(self):
        self._element.configure(
            background=self._colours.active_background.string,
            foreground=self._colours.normal_font.string)

    def _style_disabled(self):
        self._element.configure(
            background=self._colours.disabled_background.string,
            foreground=self._colours.normal_font.string)

    def _style_selected(self):
        self._element.configure(
            background=self._colours.selected_background.string,
            foreground=self._colours.selected_font.string,
            text=self._selected_text)
