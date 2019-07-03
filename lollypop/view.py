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

from lollypop.define import ViewType, App
from lollypop.logger import Logger
from lollypop.adaptive import AdaptiveView


class BaseView(AdaptiveView):
    """
        Common views members
    """

    def __init__(self):
        AdaptiveView.__init__(self)

    def populate(self):
        pass

    def stop(self):
        pass

    def disable_overlay(self):
        pass


class View(BaseView, Gtk.Grid):
    """
        Generic view
    """

    def __init__(self, view_type=ViewType.DEFAULT):
        """
            Init view
            @param view_type as ViewType
        """
        BaseView.__init__(self)
        Gtk.Grid.__init__(self)
        self._view_type = view_type
        self.__adaptive_signal_id = None
        self.__overlayed = None
        self.__scanner_signal_id = App().scanner.connect(
            "album-updated", self._on_album_updated)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self.__new_ids = []
        self._empty_message = _("No items to show")
        self._empty_icon_name = "emblem-music-symbolic"

        if view_type & ViewType.FILTERED:
            self._filter = ""
            grid = Gtk.Grid()
            grid.set_column_spacing(2)
            self.__search_entry = Gtk.SearchEntry.new()
            self.__search_entry.connect("search-changed",
                                        self._on_search_changed)
            self.__search_entry.connect("key-press-event",
                                        self.__on_key_press_event)
            self.__search_entry.show()
            button = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                                   Gtk.IconSize.MENU)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.connect("clicked", lambda x: self.__close_search_widget())
            button.show()
            grid.add(self.__search_entry)
            grid.add(button)
            grid.show()
            self.__search_bar = Gtk.SearchBar.new()
            self.__search_bar.add(grid)
            self.add(self.__search_bar)
        else:
            self._filter = None

        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.connect("leave-notify-event", self.__on_leave_notify)
        self._scrolled.show()
        self._viewport = Gtk.Viewport()
        self._scrolled.add(self._viewport)
        self._viewport.show()
        self.connect("destroy", self.__on_destroy)
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)
        if not self._view_type & ViewType.NOT_ADAPTIVE:
            self.__adaptive_signal_id = App().window.connect(
                                                    "adaptive-changed",
                                                    self._on_adaptive_changed)
        if not view_type & (ViewType.POPOVER | ViewType.SEARCH):
            self.get_style_context().add_class("view")

    def populate(self):
        """
            Populate view with default message
        """
        grid = Gtk.Grid()
        grid.set_margin_start(20)
        grid.set_margin_end(20)
        grid.set_column_spacing(20)
        label = Gtk.Label.new()
        label.set_markup("<b>%s</b>" % GLib.markup_escape_text(
            self._empty_message))
        label_style = label.get_style_context()
        label_style.add_class("text-xx-large")
        label_style.add_class("dim-label")
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        label.set_line_wrap(True)
        image = Gtk.Image.new_from_icon_name(self._empty_icon_name,
                                             Gtk.IconSize.DIALOG)
        image.get_style_context().add_class("dim-label")
        grid.add(image)
        grid.add(label)
        grid.set_vexpand(True)
        grid.set_hexpand(True)
        grid.set_property("halign", Gtk.Align.CENTER)
        grid.set_property("valign", Gtk.Align.CENTER)
        self._scrolled.hide()
        grid.set_name("lollypop_placeholder")
        grid.show_all()
        self.add(grid)

    def enable_filter(self):
        """
           Filter the view
        """
        if self._filter is not None:
            enable = not self.__search_bar.get_search_mode()
            if enable:
                width = self.get_allocated_width()
                self.__search_entry.set_size_request(min(300, width / 2), -1)
            self.__search_bar.show() if enable else self.__search_bar.hide()
            self.__search_bar.set_search_mode(enable)
            App().enable_special_shortcuts(not enable)
            if enable:
                self.__search_entry.grab_focus()

    def disable_overlay(self):
        """
            Disable overlay widget
        """
        if self.__overlayed is not None:
            self.__overlayed.show_overlay(False)

    def on_overlayed(self, widget, value):
        """
            Disable overlay on previous overlayed widget
            @param widget as AlbumWidget
            @param value as bool
        """
        if value:
            if self.__overlayed is not None:
                self.__overlayed.show_overlay(False)
            self.__overlayed = widget
        elif self.__overlayed == widget:
            self.__overlayed = None

    @property
    def filtered(self):
        """
            True if view filtered
            @return bool
        """
        return self._filter is not None and self._filter != ""

#######################
# PROTECTED           #
#######################
    def _remove_placeholder(self):
        """
            Remove any placeholder
        """
        if self._scrolled.get_visible():
            return
        for child in self.get_children():
            if child.get_name() == "lollypop_placeholder":
                child.destroy()
                break
        self._scrolled.show()

    def _filter_func(self, child):
        """
            Filter function for a Gtk.FlowBox/GtkListBox
            @param child as Gtk.FlowBoxChild/Gtk.ListBoxChild
        """
        if not self.filtered:
            if child.get_state_flags() & Gtk.StateFlags.VISITED:
                child.set_state_flags(Gtk.StateFlags.NORMAL, True)
            return True
        filter = self._filter.lower()
        if child.filter.lower().find(filter) != -1:
            return child.set_filtered(False)
        return child.set_filtered(True)

    def _on_adaptive_changed(self, window, status):
        """
            Handle adaptive mode for views
        """
        pass

    def _on_search_changed(self, entry):
        """
            Update filter
            @param entry as Gtk.Entry
        """
        self._filter = self.__search_entry.get_text()
        self._box.invalidate_filter()

    def _on_album_updated(self, scanner, album_id, added):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        pass

    def _on_map(self, widget):
        """
            Handles special shortcuts
            @param widget as Gtk.Widget
        """
        if self._filter is not None and self.__search_bar.get_search_mode():
            App().enable_special_shortcuts(False)

    def _on_unmap(self, widget):
        """
            Handles special shortcuts
            @param widget as Gtk.Widget
        """
        if self._filter is not None and self.__search_bar.get_search_mode():
            App().enable_special_shortcuts(True)

#######################
# PRIVATE             #
#######################
    def __close_search_widget(self):
        """
            Close search widget
        """
        self.__search_entry.set_text("")
        self.__search_bar.set_search_mode(False)
        self.__search_bar.hide()
        App().enable_special_shortcuts(True)

    def __on_key_press_event(self, widget, event):
        """
            If Esc, hide widget, why GTK doesn't do that?
            Otherwise, we get an ugly frame
            @param widget as Gtk.SearchEntry
            @param event as Gdk.Event
        """
        if event.keyval == 65307:
            self.__close_search_widget()
            return True

    def __on_leave_notify(self, widget, event):
        """
            Update overlays as internal widget may not have received the signal
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            self.disable_overlay()

    def __on_destroy(self, widget):
        """
            Clean up widget
            @param widget as Gtk.Widget
        """
        if self.__adaptive_signal_id is not None:
            App().window.disconnect(self.__adaptive_signal_id)
            self.__adaptive_signal_id = None
        if self.__scanner_signal_id is not None:
            App().scanner.disconnect(self.__scanner_signal_id)
            self.__scanner_signal_id = None
        self._viewport = None
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
        self._lazy_queue = []
        self.__priority_queue = []
        self.__lazy_loading_id = None
        self.__scroll_timeout_id = None
        self._scrolled.get_vadjustment().connect("value-changed",
                                                 self._on_value_changed)
        self.__start_time = time()

    def stop(self, clear=False):
        """
            Stop loading
            @param clear as bool
        """
        self.__lazy_loading_id = None
        if clear:
            self._lazy_queue = []
            self.__priority_queue = []
        View.stop(self)

    def lazy_loading(self):
        """
            Load the view in a lazy way
        """
        if self.__lazy_loading_id is None:
            self.__lazy_loading_id = GLib.idle_add(self.__lazy_loading)

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Restore backup and load
            @param widget as Gtk.Widget
        """
        View._on_map(self, widget)
        if self._lazy_queue:
            self.lazy_loading()

    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
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
            widget.populate()
        else:
            self.__lazy_loading_id = None
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
        if self.__lazy_loading_id is None:
            return
        self.__scroll_timeout_id = None
        self.__priority_queue = []
        for child in self._lazy_queue:
            if self.__is_visible(child):
                self.__priority_queue.append(child)
        self.__lazy_loading()
