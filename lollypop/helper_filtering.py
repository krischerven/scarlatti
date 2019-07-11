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

from lollypop.define import ViewType


class FilteringHelper(Gtk.Revealer):
    """
        Helper for filtering widgets Boxes
    """

    def __init__(self):
        """
            Init helper
        """
        pass

    def search_for_child(self, text):
        """
            Search child and scroll
            @param text as str
        """
        children = self.children
        for child in self.children:
            if hasattr(child, "children"):
                children += child.children
        for child in children:
            style_context = child.get_style_context()
            style_context.remove_class("typeahead")
        if not text:
            return
        for child in children:
            if child.name.lower().find(text) != -1:
                style_context = child.get_style_context()
                style_context.add_class("typeahead")
                GLib.idle_add(self._scroll_to_child, child)
                break

    def search_prev(self, text):
        """
            Search previous child and scroll
            @param text as str
        """
        previous_children = []
        found_child = None
        children = self.children
        for child in self.children:
            if hasattr(child, "children"):
                children += child.children
        for child in children:
            style_context = child.get_style_context()
            if style_context.has_class("typeahead"):
                found_child = child
                break
            previous_children.insert(0, child)
        if previous_children and found_child is not None:
            for child in previous_children:
                if child.name.lower().find(text) != -1:
                    found_child.get_style_context().remove_class("typeahead")
                    child.get_style_context().add_class("typeahead")
                    GLib.idle_add(self._scroll_to_child, child)
                    break

    def search_next(self, text):
        """
            Search previous child and scroll
            @param text as str
        """
        found = False
        previous_style_context = None
        children = self.children
        for child in self.children:
            if hasattr(child, "children"):
                children += child.children
        for child in children:
            style_context = child.get_style_context()
            if style_context.has_class("typeahead"):
                previous_style_context = style_context
                found = True
                continue
            if found and child.name.lower().find(text) != -1:
                previous_style_context.remove_class("typeahead")
                style_context.add_class("typeahead")
                GLib.idle_add(self._scroll_to_child, child)
                break

    @property
    def children(self):
        """
            Get children
            @return [Gtk.Widget]
        """
        return self._box.get_children()

#######################
# PROTECTED           #
#######################
    def _scroll_to_child(self, child):
        """
            Scroll to child
            @param child as Gtk.Widget
        """
        if self._view_type & ViewType.SCROLLED:
            coordinates = child.translate_coordinates(self._box, 0, 0)
            if coordinates:
                self._scrolled.get_vadjustment().set_value(coordinates[1])

#######################
# PRIVATE             #
#######################
