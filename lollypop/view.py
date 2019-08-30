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

from gi.repository import Gtk, GLib, Pango

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
        self.__destroyed = False
        self.__placeholder = None
        self.__main_widget = None
        self.__banner = None
        self.__scrolled_value = 0
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self.__new_ids = []
        self._empty_message = _("No items to show")
        self._empty_icon_name = "emblem-music-symbolic"

        if view_type & ViewType.SCROLLED:
            self.__scrolled = Gtk.ScrolledWindow()
            self.__event_controller = Gtk.EventControllerMotion.new(
                self.__scrolled)
            self.__event_controller.set_propagation_phase(
                Gtk.PropagationPhase.TARGET)
            self.__event_controller.connect("leave", self._on_view_leave)
            self.__scrolled.get_vadjustment().connect("value-changed",
                                                      self._on_value_changed)
            self.__scrolled.show()
            self.__scrolled.set_property("expand", True)
            self.__viewport = Gtk.Viewport()
            self.__scrolled.add(self.__viewport)
            self.__viewport.show()

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
        self.__main_widget = widget
        if self._view_type & ViewType.OVERLAY:
            self.__overlay = Gtk.Overlay.new()
            self.__overlay.show()
            if self._view_type & ViewType.SCROLLED:
                self.__overlay.add(self.__scrolled)
                self.__viewport.add(widget)
            else:
                self.__overlay.add(widget)
            if banner is not None:
                self.__overlay.add_overlay(banner)
                self.__banner = banner
            self.add(self.__overlay)
        elif self._view_type & ViewType.SCROLLED:
            self.__viewport.add(widget)
            self.add(self.__scrolled)
        else:
            self.add(widget)

    def stop(self):
        pass

    def should_reveal_header(self, adj):
        """
            Check if we need to reveal header
            @param adj as Gtk.Adjustment
            @param delta as int
            @return int
        """
        value = adj.get_value()
        reveal = self.__scrolled_value > value
        self.__scrolled_value = value
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

    @property
    def placeholder(self):
        """
            Get placeholder
            @return Gtk.Widget
        """
        if self.__placeholder is None:
            self.__placeholder = self.__get_placeholder()
        return self.__placeholder

    @property
    def view_type(self):
        """
            View type less sizing
            @return ViewType
        """
        return self._view_type & ~(ViewType.MEDIUM | ViewType.SMALL)

    @property
    def position(self):
        """
            Get scrolled position
            @return float
        """
        if self._view_type & ViewType.SCROLLED:
            position = self.__scrolled.get_vadjustment().get_value()
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
        adj = self.__scrolled.get_vadjustment()
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
        if status:
            self._view_type |= ViewType.MEDIUM
        else:
            self._view_type &= ~ViewType.MEDIUM
        if self.__placeholder is not None:
            style_context = self.__placeholder.get_style_context()
            if status:
                style_context.remove_class("text-xx-large")
                style_context.add_class("text-x-large")
            else:
                style_context.remove_class("text-x-large")
                style_context.add_class("text-xx-large")
        elif self.__banner is not None:
            self.__banner.set_view_type(self._view_type)
            self.__main_widget.set_margin_top(self.__banner.height +
                                              MARGIN_SMALL)
            if self._view_type & ViewType.SCROLLED:
                self.__scrolled.get_vscrollbar().set_margin_top(
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
                self.__main_widget.set_margin_top(self.__banner.height +
                                                  MARGIN_SMALL)
                if self._view_type & ViewType.SCROLLED:
                    self.__scrolled.get_vscrollbar().set_margin_top(
                        self.__banner.height)
            elif self._view_type & ViewType.SCROLLED:
                self.__scrolled.get_vscrollbar().set_margin_top(0)

    def _on_album_updated(self, scanner, album_id, added):
        pass

    def _on_map(self, widget):
        """
            Delayed adaptive mode
        """
        self._on_adaptive_changed(App().window, App().window.is_adaptive)

    def _on_unmap(self, widget):
        pass

#######################
# PRIVATE             #
#######################
    def __get_placeholder(self):
        """
            Get view placeholder
            @return Gtk.Widget
        """
        label = Gtk.Label.new()
        label.show()
        label.set_markup("%s" % GLib.markup_escape_text(self._empty_message))
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        label.set_line_wrap(True)
        label_style = label.get_style_context()
        label_style.add_class("dim-label")
        if App().window.is_adaptive:
            label_style.add_class("text-x-large")
        else:
            label_style.add_class("text-xx-large")
        label_style.add_class("dim-label")
        image = Gtk.Image.new_from_icon_name(self._empty_icon_name,
                                             Gtk.IconSize.DIALOG)
        image.show()
        image.get_style_context().add_class("dim-label")
        placeholder = Gtk.Grid()
        placeholder.show()
        placeholder.set_margin_start(20)
        placeholder.set_margin_end(20)
        placeholder.set_column_spacing(20)
        placeholder.add(image)
        placeholder.add(label)
        placeholder.set_vexpand(True)
        placeholder.set_hexpand(True)
        placeholder.set_property("halign", Gtk.Align.CENTER)
        placeholder.set_property("valign", Gtk.Align.CENTER)
        return placeholder

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
        self.__scrolled_position = None
        self.__lazy_loading_id = None
        self.__start_time = time()

    def stop(self, clear=False):
        """
            Stop loading
            @param clear as bool
        """
        self.__loading_state = LoadingState.ABORTED
        self.__lazy_loading_id = None
        if clear:
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

    def set_populated_scrolled_position(self, position):
        """
            Set scrolled position on populated
            @param position as int
        """
        if self._view_type & ViewType.SCROLLED:
            self.__scrolled_position = position

    def set_external_scrolled(self, scrolled):
        """
            Set an external scrolled window for loading
            @param scrolled as Gtk.ScrolledWindow
        """
        self.__scrolled = scrolled
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
        # Wait for viewport allocation to restore scrolled position
        if self.__scrolled_position is not None:
            self.__viewport.connect("size-allocate",
                                    self.__on_viewport_size_allocated)
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
        scrolled_alloc = self.__scrolled.get_allocation()
        try:
            (x, y) = widget.translate_coordinates(self.__scrolled, 0, 0)
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

    def __on_viewport_size_allocated(self, viewport, allocation):
        """
            Restore scrolled position
            @param viewport as Gtk.Viewport
            @param allocation as Gdk.Rectangle
        """
        if allocation.height > 1 and self.__scrolled_position is not None:
            self.__viewport.disconnect_by_func(
                self.__on_viewport_size_allocated)
            self.__scrolled.get_vadjustment().set_value(
                self.__scrolled_position)
            self.__scrolled_position = None
