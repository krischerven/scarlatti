# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Gdk

from lollypop.define import App


class TypeAheadWidget(Gtk.Revealer):
    """
        Type ahead widget
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Revealer.__init__(self)
        self.__multi_press_left = None
        self.__multi_press_right = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/TypeAhead.ui")
        builder.connect_signals(self)
        widget = builder.get_object("widget")
        self.__entry = builder.get_object("entry")
        self.__next_button = builder.get_object("next_button")
        self.__prev_button = builder.get_object("prev_button")
        self.__next_button.connect("clicked", lambda x: self.__search_next())
        self.__prev_button.connect("clicked", lambda x: self.__search_prev())
        self.add(widget)

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
        view = App().window.container.focused_view
        if view is not None:
            view.search_for_child(entry.get_text())

    def _on_type_ahead_activate(self, entry):
        """
            Activate row
            @param entry as Gtk.Entry
        """
        view = App().window.container.focused_view
        if view is not None:
            view.activate_child()

    def _on_close_button_clicked(self, button):
        """
            Close widget
            @param button as Gtk.Button
        """
        self.set_reveal_child(False)

    # FIXME GTK4
    def _on_entry_key_press_event(self, entry, event):
        """
            Handle special keys
            @param entry as Gtk.Entry
            @param Event as Gdk.EventKey
        """
        if event.keyval == Gdk.KEY_Up or event.keyval == Gdk.KEY_Down:
            return True
        elif event.keyval == Gdk.KEY_Escape:
            App().window.container.show_filter()

    # FIXME GTK4
    def _on_entry_key_release_event(self, entry, event):
        """
            Handle special keys
            @param entry as Gtk.Entry
            @param Event as Gdk.EventKey
        """
        if event.keyval == Gdk.KEY_Up:
            self.__search_prev()
        elif event.keyval == Gdk.KEY_Down:
            self.__search_next()

#######################
# PRIVATE             #
#######################
    def __search_prev(self):
        """
            Search previous item
        """
        view = App().window.container.focused_view
        if view is not None:
            view.search_prev(self.__entry.get_text())

    def __search_next(self):
        """
            Search next item
        """
        view = App().window.container.focused_view
        if view is not None:
            view.search_next(self.__entry.get_text())
