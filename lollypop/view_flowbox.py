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

from lollypop.view import LazyLoadingView
from lollypop.define import ViewType
from lollypop.utils import get_font_height


class FlowBoxView(LazyLoadingView):
    """
        Lazy loading FlowBox
    """

    def __init__(self, view_type=ViewType.SCROLLED):
        """
            Init flowbox view
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type | ViewType.FILTERED)
        self.__adaptive_signal_id = None
        self._widget_class = None
        self.__font_height = get_font_height()
        self._box = Gtk.FlowBox()
        self._box.set_filter_func(self._filter_func)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        # Allow lazy loading to not jump up and down
        self._box.set_homogeneous(True)
        self._box.set_max_children_per_line(1000)
        self._box.connect("child-activated", self._on_item_activated)
        self._box.show()

        if view_type & ViewType.SCROLLED:
            self._viewport.set_property("valign", Gtk.Align.START)
            self._viewport.set_property("margin", 5)
            self._scrolled.set_property("expand", True)
            self.add(self._scrolled)

    def populate(self, items):
        """
            Populate items
            @param items
        """
        if items and self._box.get_visible():
            GLib.idle_add(self._add_items, items)
        else:
            LazyLoadingView.populate(self)

    @property
    def font_height(self):
        """
            Get font height
            @return int
        """
        return self.__font_height

    @property
    def children(self):
        """
            Get box children
            @return [Gtk.Widget]
        """
        return self._box.get_children()

#######################
# PROTECTED           #
#######################
    def _get_label_height(self):
        """
            Get wanted label height
            @return int
        """
        return 0

    def _add_items(self, items, *args):
        """
            Add items to the view
            Start lazy loading
            @param items as [int]
            @return added widget
        """
        if self._lazy_queue is None or self._viewport is None:
            return
        if items:
            widget = self._widget_class(
                items.pop(0), *args, self.__font_height)
            self._box.insert(widget, -1)
            widget.show()
            self._lazy_queue.append(widget)
            GLib.idle_add(self._add_items, items)
            return widget
        else:
            self.lazy_loading()
            if self._view_type & ViewType.SCROLLED:
                if self._viewport.get_child() is None:
                    self._viewport.add(self._box)
            elif self._box not in self.get_children():
                self.add(self._box)
        return None

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self._box.get_children():
            child.set_selection()

    def _on_item_activated(self, flowbox, widget):
        pass

    def _on_adaptive_changed(self, window, status):
        """
            Update artwork
            @param window as Window
            @param status as bool
        """
        def update_artwork(children):
            if children:
                child = children.pop(0)
                child.set_artwork()
                GLib.idle_add(update_artwork, children)

        self.stop(True)
        if status:
            view_type = self._view_type | ViewType.MEDIUM
        else:
            view_type = self._view_type & ~ViewType.MEDIUM
        children = self._box.get_children()
        for child in children:
            child.set_view_type(view_type)
            child.disable_artwork()
            self._lazy_queue.append(child)
        self.lazy_loading()

#######################
# PRIVATE             #
#######################
