# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk, GLib

from lollypop.define import App, MARGIN_SMALL


class TypeAheadWidget(Gtk.Revealer):
    """
        Type ahead widget
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Revealer.__init__(self)
        self.__list_two_map_signal_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/TypeAhead.ui")
        builder.connect_signals(self)
        widget = builder.get_object("widget")
        widget.set_hexpand(True)
        widget.set_property("halign", Gtk.Align.CENTER)
        widget.set_margin_top(MARGIN_SMALL)
        widget.set_margin_bottom(MARGIN_SMALL)
        self.__entry = builder.get_object("entry")
        self.__next_button = builder.get_object("next_button")
        self.__prev_button = builder.get_object("prev_button")
        self.__next_button.connect("clicked", lambda x: self.__search_next())
        self.__prev_button.connect("clicked", lambda x: self.__search_prev())
        self.__list_one_toggle = builder.get_object("list_one_toggle")
        self.__list_two_toggle = builder.get_object("list_two_toggle")
        self.__view_toggle = builder.get_object("view_toggle")
        self.__view_toggle.set_active(True)
        self.add(widget)

    def update_buttons(self):
        """
            Show hide buttons
        """
        def hide_button(l):
            App().window.container.list_two.disconnect(
                self.__list_two_map_signal_id)
            App().window.container.list_two.disconnect_by_func(hide_button)
            self.__list_two_map_signal_id = None
            self.__list_two_toggle.hide()

        def show_button(l):
            self.__list_two_toggle.show()

        self.__show_toggle_buttons(App().settings.get_value("show-sidebar") and
                                   not App().window.is_adaptive)
        if App().window.container.list_one is None:
            self.__list_one_toggle.hide()
        else:
            self.__list_one_toggle.show()
        if App().window.container.list_two is not None:
            if App().window.container.list_two.get_visible():
                self.__list_two_toggle.show()
            else:
                self.__list_two_toggle.hide()
            if self.__list_two_map_signal_id is None:
                self.__list_two_map_signal_id =\
                    App().window.container.list_two.connect("map",
                                                            show_button)
                App().window.container.list_two.connect("unmap", hide_button)
        else:
            self.__list_two_toggle.hide()

    @property
    def entry(self):
        """
            Get popover entry
            @return Gtk.Entry
        """
        return self.__entry

#######################
# PROTECTED           #
#######################
    def _on_type_ahead_changed(self, entry):
        """
            Filter current widget
            @param entry as Gtk.entry
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.search_for_child(entry.get_text().lower())

    def _on_type_ahead_activate(self, entry):
        """
            Activate row
            @param entry as Gtk.Entry
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.activate_child()
            GLib.idle_add(self.__activate_next_button)
            self.__entry.set_text("")
            self.__entry.grab_focus()

    def _on_entry_key_press_event(self, entry, event):
        """
            Handle special keys
            @param entry as Gtk.Entry
            @param Event as Gdk.EventKey
        """
        if (event.state & Gdk.ModifierType.SHIFT_MASK and
                event.state & Gdk.ModifierType.CONTROL_MASK) or\
                event.keyval == Gdk.KEY_Up or\
                event.keyval == Gdk.KEY_Down:
            return True

    def _on_entry_key_release_event(self, entry, event):
        """
            Handle special keys
            @param entry as Gtk.Entry
            @param Event as Gdk.EventKey
        """
        if event.state & (Gdk.ModifierType.SHIFT_MASK |
                          Gdk.ModifierType.CONTROL_MASK):
            if event.keyval == Gdk.KEY_Right:
                self.__activate_next_button()
            elif event.keyval == Gdk.KEY_Left:
                self.__activate_prev_button()
        elif event.keyval == Gdk.KEY_Up:
            self.__search_prev()
        elif event.keyval == Gdk.KEY_Down:
            self.__search_next()

    def _on_button_toggled(self, button):
        """
            Untoggle other buttons
            @param button as Gtk.Button
        """
        if not button.get_active():
            return
        buttons = self.__get_buttons()
        for _button in buttons:
            if _button != button:
                _button.set_active(False)

#######################
# PRIVATE             #
#######################
    def __search_prev(self):
        """
            Search previous item
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.search_prev(self.__entry.get_text().lower())

    def __search_next(self):
        """
            Search next item
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.search_next(self.__entry.get_text().lower())

    def __show_toggle_buttons(self, show):
        """
            Show toggle buttons
            @param show as bool
        """
        if show:
            self.__list_one_toggle.show()
            self.__list_two_toggle.show()
            self.__view_toggle.show()
        else:
            self.__list_one_toggle.hide()
            self.__list_two_toggle.hide()
            self.__view_toggle.hide()

    def __get_widget(self):
        """
            Get widget for activated button
            @return Gtk.Widget
        """
        if self.__list_one_toggle.get_active():
            return App().window.container.list_one
        elif self.__list_two_toggle.get_active():
            return App().window.container.list_two
        else:
            return App().window.container.stack

    def __get_buttons(self):
        """
            Get current buttons
            @return [Gtk.ToggleButton]
        """
        buttons = []
        for button in [self.__list_one_toggle,
                       self.__list_two_toggle,
                       self.__view_toggle]:
            if button.get_visible():
                buttons.append(button)
        return buttons

    def __activate_next_button(self):
        """
            Activate next button
        """
        active = None
        buttons = self.__get_buttons()
        for button in buttons:
            if button.get_active():
                active = button
                break
        index = buttons.index(active)
        if index + 1 < len(buttons):
            buttons[index + 1].set_active(True)

    def __activate_prev_button(self):
        """
            Activate prev button
        """
        active = None
        buttons = self.__get_buttons()
        for button in buttons:
            if button.get_active():
                active = button
                break
        index = buttons.index(active)
        if index > 0:
            buttons[index - 1].set_active(True)
