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

from gi.repository import Gtk

from lollypop.widgets_typeahead import TypeAheadWidget
from lollypop.define import App


class FilterContainer:
    """
        Filtering management
    """

    def __init__(self):
        """
            Init container
        """
        self.__widgets = []
        self.__index = 0
        self.__type_ahead = TypeAheadWidget()
        self.__type_ahead.entry.connect("activate",
                                        self.__on_type_ahead_activate)
        self.__type_ahead.entry.connect("changed",
                                        self.__on_type_ahead_changed)
        self.__type_ahead.left_button.connect("clicked",
                                              self.__on_left_button_clicked)
        self.__type_ahead.right_button.connect("clicked",
                                               self.__on_right_button_clicked)
        self.__type_ahead.show()
        self.__search_bar = Gtk.SearchBar.new()
        self.__search_bar.add(self.__type_ahead)
        self.__search_bar.show()
        self._grid.add(self.__search_bar)
        self._grid.add(self._paned_one)

    def add_widget_to_filter(self, widget, index):
        """
            Add new widget to filter
            @param widget as Widget
            @param index as int
        """
        self.__widgets.insert(index, widget)
        widget.connect("map", lambda x: self.__update_internals())
        widget.connect("destroy", self.__on_destroy)

    def left(self):
        """
            Move left
        """
        previous = self.__previous_widget()
        if previous is not None:
            self.__index = self.__widgets.index(previous)
            self.__update_internals()

    def right(self):
        """
            Move right
        """
        previous = self.__next_widget()
        if previous is not None:
            self.__index = self.__widgets.index(previous)
            self.__update_internals()

    def show_filter(self):
        """
            Show filtering widget
        """
        search_mode = not self.__search_bar.get_search_mode()
        self.__search_bar.set_search_mode(search_mode)
        if search_mode:
            App().enable_special_shortcuts(False)
            self.__update_internals()
            self.__type_ahead.entry.grab_focus()
        else:
            App().enable_special_shortcuts(True)
            self.__type_ahead.entry.set_text("")
            for widget in self.__widgets:
                widget.get_style_context().remove_class("red-border")

############
# PRIVATE  #
############
    def __next_widget(self):
        """
            Get next widget
            @return Gtk.Widget
        """
        i = self.__index + 1
        while i < len(self.__widgets):
            if self.__widgets[i].get_visible():
                return self.__widgets[i]
            i += 1
        return None

    def __previous_widget(self):
        """
            Get previous widget
            @return Gtk.Widget
        """
        i = self.__index - 1
        while i >= 0:
            if self.__widgets[i].get_visible():
                return self.__widgets[i]
            i -= 1
        return None

    def __update_internals(self):
        """
            Update buttons and position
        """
        if self.__search_bar.get_search_mode():
            self.__type_ahead.left_button.set_sensitive(
                self.__previous_widget() is not None)
            self.__type_ahead.right_button.set_sensitive(
                self.__next_widget() is not None)
            for widget in self.__widgets:
                widget.get_style_context().remove_class("red-border")
            self.__widgets[self.__index].get_style_context().add_class(
                    "red-border")

    def __on_destroy(self, widget):
        """
            Remove widget
            @param widget as Gtk.Widget
        """
        self.__widgets.remove(widget)
        if self.__index > len(self.__widgets):
            self.__index -= 1

    def __on_type_ahead_changed(self, entry):
        """
            Filter current widget
            @param entry as Gtk.entry
        """
        self.__widgets[self.__index].search_for_child(entry.get_text().lower())

    def __on_type_ahead_activate(self, entry):
        """
            Activate row
            @param entry as Gtk.Entry
        """
        self.__widgets[self.__index].activate_child()
        self.show_filter()
        for widget in self.__widgets:
            widget.get_style_context().remove_class("red-border")

    def __on_left_button_clicked(self, button):
        """
            Go left
            @param button as Gtk.button
        """
        self.left()

    def __on_right_button_clicked(self, button):
        """
            Go right
            @param button as Gtk.button
        """
        self.right()
