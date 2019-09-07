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

from time import time
from gettext import gettext as _
import gc

from lollypop.define import ViewType, App, LoadingState, MARGIN_SMALL
from lollypop.logger import Logger
from lollypop.adaptive import AdaptiveView
from lollypop.helper_signals import SignalsHelper, signals_map


class View(AdaptiveView, Gtk.Grid, SignalsHelper):
    """
        Generic view
    """

    @signals_map
    def __init__(self, view_type=ViewType.DEFAULT):
        """
            Init view
            @param view_type as ViewType
        """
        AdaptiveView.__init__(self)
        Gtk.Grid.__init__(self)
        self._view_type = view_type
        self.__scrolled_position = None
        self.__destroyed = False
        self.__banner = None
        self.__placeholder = None
        self._scrolled_value = 0
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self.__new_ids = []
        self._empty_message = _("No items to show")
        self._empty_icon_name = "emblem-music-symbolic"

        if view_type & ViewType.SCROLLED:
            self._scrolled = Gtk.ScrolledWindow()
            self.__event_controller = Gtk.EventControllerMotion.new(
                self._scrolled)
            self.__event_controller.set_propagation_phase(
                Gtk.PropagationPhase.TARGET)
            self.__event_controller.connect("leave", self._on_view_leave)
            self._scrolled.get_vadjustment().connect("value-changed",
                                                     self._on_value_changed)
            self._scrolled.show()
            self._scrolled.set_property("expand", True)
            self.__viewport = Gtk.Viewport()
            self._scrolled.add(self.__viewport)
            self.__viewport.show()

        # Stack for placeholder
        self.__stack = Gtk.Stack.new()
        self.__stack.show()
        self.__stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self.connect("destroy", self.__on_destroy)
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)
        return [
            (App().window, "adaptive-changed", "_on_adaptive_changed"),
        ]

    def add_widget(self, widget, banner=None):
        """
            Add widget to view
            Add banner if ViewType.OVERLAY
            @param widget as Gtk.Widget
        """
        self.__stack.add_named(widget, "main")
        if self._view_type & ViewType.OVERLAY:
            self.__overlay = Gtk.Overlay.new()
            self.__overlay.show()
            if self._view_type & ViewType.SCROLLED:
                self.__overlay.add(self._scrolled)
                self.__viewport.add(self.__stack)
            else:
                self.__overlay.add(self.__stack)
            if banner is not None:
                self.__overlay.add_overlay(banner)
                self.__banner = banner
            self.add(self.__overlay)
        elif self._view_type & ViewType.SCROLLED:
            self.__viewport.add(self.__stack)
            self.add(self._scrolled)
        else:
            self.add(self.__stack)

    def stop(self):
        pass

    def show_placeholder(self, show, new_text=None):
        """
            Show placeholder
            @param show as bool
        """
        if show:
            if self.__placeholder is not None:
                GLib.timeout_add(200, self.__placeholder.destroy)
            message = new_text\
                if new_text is not None\
                else self._empty_message
            from lollypop.placeholder import Placeholder
            self.__placeholder = Placeholder(message, self._empty_icon_name)
            self.__placeholder.show()
            self.__stack.add(self.__placeholder)
            self.__stack.set_visible_child(self.__placeholder)
        else:
            self.__stack.set_visible_child_name("main")

    def should_reveal_header(self, adj):
        """
            Check if we need to reveal header
            @param adj as Gtk.Adjustment
            @param delta as int
            @return int
        """
        value = adj.get_value()
        reveal = self._scrolled_value > value
        self._scrolled_value = value
        return reveal

    def search_for_child(self, text):
        """
            Search and hilight child in current view
            @param text as str
        """
        pass

    def activate_child(self):
        """
            Activate hilighted child
        """
        pass

    def search_prev(self, text):
        """
            Search and hilight prev child
            @param text as str
        """
        pass

    def search_next(self, text):
        """
            Search and hilight next child
            @param text as str
        """
        pass

    def set_populated_scrolled_position(self, position):
        """
            Set scrolled position on populated
            @param position as int
        """
        if self._view_type & ViewType.SCROLLED:
            self.__scrolled_position = position

    @property
    def view_type(self):
        """
            View type less sizing
            @return ViewType
        """
        return self._view_type & ~(ViewType.ADAPTIVE | ViewType.SMALL)

    @property
    def position(self):
        """
            Get scrolled position
            @return float
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        return position

    @property
    def destroyed(self):
        """
            True if widget has been destroyed
            @return bool
        """
        return self.__destroyed

#######################
# PROTECTED           #
#######################
    def _on_view_leave(self, event_controller):
        pass

    def _on_banner_scroll(self, banner, x, y):
        """
            Pass to scrolled
            @param banner as BannerWidget
            @param x as float
            @param y as float
        """
        if y > 0:
            y = 100
        else:
            y = -100
        adj = self._scrolled.get_vadjustment()
        new_value = adj.get_value() + y
        lower = adj.get_lower()
        upper = adj.get_upper() - adj.get_page_size()
        adj.set_value(max(lower, min(new_value, upper)))

    def _on_adaptive_changed(self, window, status):
        """
            Handle adaptive mode for views
            @param window as Window
            @param status as bool
            @return bool
        """
        view_type = self._view_type
        if self.__placeholder is not None and self.__placeholder.is_visible():
            self.__placeholder.set_adaptive(status)
        if status:
            self._view_type |= ViewType.ADAPTIVE
        else:
            self._view_type &= ~ViewType.ADAPTIVE
        if self.__banner is not None:
            self.__banner.set_view_type(self._view_type)
            main_widget = self.__stack.get_child_by_name("main")
            main_widget.set_margin_top(self.__banner.height + MARGIN_SMALL)
            if self._view_type & ViewType.SCROLLED:
                self._scrolled.get_vscrollbar().set_margin_top(
                    self.__banner.height)
        return view_type != self._view_type

    def _on_value_changed(self, adj):
        """
            Update margin if needed
        """
        if self.__banner is not None:
            reveal = self.should_reveal_header(adj)
            self.__banner.set_reveal_child(reveal)
            if reveal:
                main_widget = self.__stack.get_child_by_name("main")
                main_widget.set_margin_top(self.__banner.height + MARGIN_SMALL)
                if self._view_type & ViewType.SCROLLED:
                    self._scrolled.get_vscrollbar().set_margin_top(
                        self.__banner.height)
            elif self._view_type & ViewType.SCROLLED:
                self._scrolled.get_vscrollbar().set_margin_top(0)

    def _on_album_updated(self, scanner, album_id, added):
        pass

    def _on_map(self, widget):
        """
            Delayed adaptive mode
        """
        self._on_adaptive_changed(App().window, App().window.is_adaptive)
        # Wait for stack allocation to restore scrolled position
        if self.__scrolled_position is not None:
            self.__stack.connect("size-allocate",
                                 self.__on_stack_size_allocated)

    def _on_unmap(self, widget):
        pass

#######################
# PRIVATE             #
#######################
    def __on_stack_size_allocated(self, stack, allocation):
        """
            Restore scrolled position
            @param stack as Gtk.Stack
            @param allocation as Gdk.Rectangle
        """
        if self.__scrolled_position is not None and\
                allocation.height > self.__scrolled_position:
            stack.disconnect_by_func(self.__on_stack_size_allocated)
            self._scrolled.get_vadjustment().set_value(
                self.__scrolled_position)
            self.__scrolled_position = None

    def __on_destroy(self, widget):
        """
            Clean up widget
            @param widget as Gtk.Widget
        """
        self.__destroyed = True
        gc.collect()


class LazyLoadingView(View):
    """
        Lazy loading for view
    """

    def __init__(self, view_type=ViewType.DEFAULT):
        """
            Init lazy loading
            @param view_type as ViewType
        """
        View.__init__(self, view_type)
        self.__loading_state = LoadingState.NONE
        self._lazy_queue = []
        self.__priority_queue = []
        self.__scroll_timeout_id = None
        self.__lazy_loading_id = None
        self.__start_time = time()

    def pause(self):
        """
            Pause loading
        """
        self.__loading_state = LoadingState.ABORTED
        self.__lazy_loading_id = None
        if self.__scroll_timeout_id is not None:
            GLib.source_remove(self.__scroll_timeout_id)
            self.__scroll_timeout_id = None
        View.stop(self)

    def stop(self):
        """
            Stop loading and clear queue
        """
        self.__loading_state = LoadingState.FINISHED
        self.__lazy_loading_id = None
        if self.__scroll_timeout_id is not None:
            GLib.source_remove(self.__scroll_timeout_id)
            self.__scroll_timeout_id = None
        self._lazy_queue = []
        self.__priority_queue = []
        View.stop(self)

    def lazy_loading(self):
        """
            Load the view in a lazy way
        """
        # He we keep id just to check we are in current load
        if self.__lazy_loading_id is None:
            self.__lazy_loading_id = GLib.idle_add(self.__lazy_loading)

    def set_external_scrolled(self, scrolled):
        """
            Set an external scrolled window for loading
            @param scrolled as Gtk.ScrolledWindow
        """
        self._scrolled = scrolled
        scrolled.get_vadjustment().connect("value-changed",
                                           self._on_value_changed)

    @property
    def is_populated(self):
        """
            True if populated
            @return bool
        """
        return self.__loading_state == LoadingState.FINISHED

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Restore backup and load
            @param widget as Gtk.Widget
        """
        View._on_map(self, widget)
        if self.__loading_state == LoadingState.ABORTED and self._lazy_queue:
            self.lazy_loading()

    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        View._on_value_changed(self, adj)
        if not self._lazy_queue:
            return False
        if self.__scroll_timeout_id is not None:
            GLib.source_remove(self.__scroll_timeout_id)
        self.__scroll_timeout_id = GLib.timeout_add(200, self.__lazy_or_not)

    def _on_populated(self, widget, lazy_loading_id):
        """
            Add another album/disc
            @param widget as AlbumWidget/TracksView
            @parma lazy_loading_id as int
        """
        if lazy_loading_id != self.__lazy_loading_id:
            return
        if not widget.is_populated:
            widget.populate()
        else:
            self.__lazy_loading()

#######################
# PRIVATE             #
#######################
    def __lazy_loading(self):
        """
            Load the view in a lazy way
        """
        widget = None
        if self.__priority_queue:
            widget = self.__priority_queue.pop(0)
            self._lazy_queue.remove(widget)
        elif self._lazy_queue:
            widget = self._lazy_queue.pop(0)
        if widget is not None:
            widget.connect("populated",
                           self._on_populated,
                           self.__lazy_loading_id)
            # https://gitlab.gnome.org/World/lollypop/issues/1884
            GLib.idle_add(widget.populate)
        else:
            self.__lazy_loading_id = None
            self.__loading_state = LoadingState.FINISHED
            Logger.debug("LazyLoadingView::lazy_loading(): %s",
                         time() - self.__start_time)

    def __is_visible(self, widget):
        """
            Is widget visible in scrolled
            @param widget as Gtk.Widget
        """
        widget_alloc = widget.get_allocation()
        scrolled_alloc = self._scrolled.get_allocation()
        try:
            (x, y) = widget.translate_coordinates(self._scrolled, 0, 0)
            return (y > -widget_alloc.height or y >= 0) and\
                y < scrolled_alloc.height
        except:
            return True

    def __lazy_or_not(self):
        """
            Add visible widgets to lazy queue
        """
        self.__scroll_timeout_id = None
        if self.__lazy_loading_id is None:
            return
        self.__priority_queue = []
        for child in self._lazy_queue:
            if self.__is_visible(child):
                self.__priority_queue.append(child)
