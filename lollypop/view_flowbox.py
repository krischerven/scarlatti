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
from lollypop.helper_filtering import FilteringHelper
from lollypop.helper_gestures import GesturesHelper
from lollypop.define import ViewType, MARGIN
from lollypop.utils import get_font_height, popup_widget


class FlowBoxView(FilteringHelper, LazyLoadingView, GesturesHelper):
    """
        Lazy loading FlowBox
    """

    def __init__(self, view_type=ViewType.SCROLLED):
        """
            Init flowbox view
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type)
        FilteringHelper.__init__(self)
        self._widget_class = None
        self._items = []
        self.__hovered_child = None
        self.__font_height = get_font_height()
        self._box = Gtk.FlowBox()
        self._box.get_style_context().add_class("padding")
        # Allow lazy loading to not jump up and down
        self._box.set_homogeneous(True)
        self._box.set_vexpand(True)
        self._box.set_max_children_per_line(1000)
        self._box.set_row_spacing(MARGIN)
        self._box.set_column_spacing(MARGIN)
        self._box.set_property("valign", Gtk.Align.START)
        self._box.connect("child-activated", self._on_child_activated)
        self._box.show()
        if not view_type & ViewType.SMALL:
            self.__event_controller = Gtk.EventControllerMotion.new(self._box)
            self.__event_controller.connect("motion", self.__on_box_motion)
        GesturesHelper.__init__(self, self._box)

    def populate(self, items):
        """
            Populate items
            @param items
        """
        self._items = list(items)
        if items:
            GLib.idle_add(self._add_items, items)

    def activate_child(self):
        """
            Activated typeahead row
        """
        self._box.unselect_all()
        for row in self._box.get_children():
            style_context = row.get_style_context()
            if style_context.has_class("typeahead"):
                row.activate()
            style_context.remove_class("typeahead")

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
    def _get_menu_widget(self, child):
        """
            Get menu widget
            @param child as Gtk.FlowBoxChild
            @return Gtk.Widget
        """
        return None

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
        """
        if self._lazy_queue is None or self.destroyed:
            return
        if items:
            widget = self._widget_class(
                items.pop(0), *args, self.__font_height)
            widget.set_property("halign", Gtk.Align.START)
            widget.set_property("valign", Gtk.Align.START)
            self._box.insert(widget, -1)
            widget.show()
            self._lazy_queue.append(widget)
            GLib.idle_add(self._add_items, items)
        else:
            self.lazy_loading()

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self._box.get_children():
            child.set_selection()

    def _on_child_activated(self, flowbox, child):
        pass

    def _on_adaptive_changed(self, window, status):
        """
            Update artwork
            @param window as Window
            @param status as bool
        """
        if LazyLoadingView._on_adaptive_changed(self, window, status):
            self.stop(True)
            children = self._box.get_children()
            for child in children:
                child.set_view_type(self._view_type)
                child.disable_artwork()
                self._lazy_queue.append(child)
            self.lazy_loading()

    def _on_view_leave(self, event_controller):
        """
            Unselect selected child
            @param event_controller as Gtk.EventControllerMotion
        """
        self.__unselect_selected()

    def _on_secondary_press_gesture(self, x, y, event):
        """
            Popup menu for artist at position
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        self._on_primary_long_press_gesture(x, y)

    def _on_primary_long_press_gesture(self, x, y):
        """
            Popup menu for artist at position
            @param x as int
            @param y as int
        """
        child = self._box.get_child_at_pos(x, y)
        if child is None or child.artwork is None:
            return
        self.__popup_menu(child)

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, child):
        """
            Popup album menu at position
            @param child ad RoundedArtistWidget
        """
        menu_widget = self._get_menu_widget(child)
        if menu_widget is not None:
            menu_widget.show()
            popup_widget(menu_widget, child.artwork)

    def __unselect_selected(self):
        """
            Unselect selected child
        """
        if self.__hovered_child is not None:
            self.__hovered_child.set_opacity(1)
            self.__hovered_child = None

    def __on_box_motion(self, event_controller, x, y):
        """
            Update current selected child
            @param event_controller as Gtk.EventControllerMotion
            @param x as int
            @param y as int
        """
        child = self._box.get_child_at_pos(x, y)
        if child == self.__hovered_child:
            return
        elif child is not None:
            child.set_opacity(0.9)
            self.__unselect_selected()
            self.__hovered_child = child
