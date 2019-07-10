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

from gi.repository import Gtk, GLib


class FilteringHelper(Gtk.Revealer):
    """
        Helper for filtered Gtk.FlowBox/Gtk.ListBox
    """

    def __init__(self):
        """
            Init helper
        """
        pass

    def search_for_child(self, text):
        """
            Search row and scroll
            @param text as str
        """
        for row in self._box.get_children():
            style_context = row.get_style_context()
            style_context.remove_class("typeahead")
        if not text:
            return
        for row in self._box.get_children():
            if row.name.lower().find(text) != -1:
                style_context = row.get_style_context()
                style_context.add_class("typeahead")
                GLib.idle_add(self._scroll_to_row, row)
                break

    def search_prev(self, text):
        """
            Search previous row and scroll
            @param text as str
        """
        previous_rows = []
        found_row = None
        for row in self._box.get_children():
            style_context = row.get_style_context()
            if style_context.has_class("typeahead"):
                found_row = row
                break
            previous_rows.insert(0, row)
        if previous_rows and found_row is not None:
            for row in previous_rows:
                if row.name.lower().find(text) != -1:
                    found_row.get_style_context().remove_class("typeahead")
                    row.get_style_context().add_class("typeahead")
                    GLib.idle_add(self._scroll_to_row, row)
                    break

    def search_next(self, text):
        """
            Search previous row and scroll
            @param text as str
        """
        found = False
        previous_style_context = None
        for row in self._box.get_children():
            style_context = row.get_style_context()
            if style_context.has_class("typeahead"):
                previous_style_context = style_context
                found = True
                continue
            if found and row.name.lower().find(text) != -1:
                previous_style_context.remove_class("typeahead")
                style_context.add_class("typeahead")
                GLib.idle_add(self._scroll_to_row, row)
                break

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
