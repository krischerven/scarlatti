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

from lollypop.define import ArtSize, App


class OverlayHelper:
    """
        An overlay helper
    """

    def __init__(self):
        """
            Init helper
        """
        self._show_overlay = False
        self._lock_overlay = False
        self._spinner = None
        self._watch_loading = False
        self.__timeout_id = None
        self.__loading_changed_id = None
        self._pixel_size = ArtSize.BIG / 9

    def lock_overlay(self, lock):
        """
            Lock overlay
            @param lock as bool
        """
        self._lock_overlay = lock

    def show_overlay(self, set):
        """
            Set overlay
            @param set as bool
        """
        # Remove enter notify timeout
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        self._show_overlay_func(set)

    @property
    def is_overlay(self):
        """
            True if overlayed or going to be
        """
        return self._show_overlay

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, show_overlay):
        """
            Set overlay
            @param show_overlay as bool
        """
        if show_overlay:
            self._big_grid = Gtk.Grid()
            self._big_grid.set_property("halign", Gtk.Align.START)
            self._big_grid.set_property("valign", Gtk.Align.END)
            self._big_grid.set_margin_start(6)
            self._big_grid.set_margin_bottom(6)
            self._big_grid.show()
            self._overlay.add_overlay(self._big_grid)
            self._small_grid = Gtk.Grid()
            self._small_grid.set_margin_bottom(6)
            self._small_grid.set_margin_end(6)
            self._small_grid.set_property("halign", Gtk.Align.END)
            self._small_grid.set_property("valign", Gtk.Align.END)
            self._overlay.add_overlay(self._small_grid)
            self._small_grid.show()
            self._big_grid.get_style_context().add_class("rounded-icon")
            self._small_grid.get_style_context().add_class(
                    "squared-icon-small")
        else:
            self._big_grid.destroy()
            self._big_grid = None
            self._small_grid.destroy()
            self._small_grid = None
        self._show_overlay = show_overlay
        self.emit("overlayed", show_overlay)

    def _on_enter_notify(self, widget, event):
        """
            Show overlay buttons after a timeout
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        if self._artwork is None:
            return
        if self.__loading_changed_id is None and self._watch_loading:
            self.__loading_changed_id = App().player.connect(
                "loading-changed", self._on_loading_changed)
            self.connect("unmap", self.__on_unmap)
        self._artwork.set_opacity(0.9)
        if self.__timeout_id is None:
            self.__timeout_id = GLib.timeout_add(250,
                                                 self._on_enter_notify_timeout)

    def _on_leave_notify(self, widget, event):
        """
            Hide overlay buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            if self._artwork is not None:
                self._artwork.set_opacity(1)
            # Remove enter notify timeout
            if self.__timeout_id is not None:
                GLib.source_remove(self.__timeout_id)
                self.__timeout_id = None
            if self._show_overlay:
                self._show_overlay_func(False)

    def _on_enter_notify_timeout(self):
        """
            Show overlay buttons
        """
        self.__timeout_id = None
        if not self._show_overlay:
            self._show_overlay_func(True)

    def _on_popover_closed(self, widget):
        """
            Remove selected style
            @param widget as Popover
        """
        self._lock_overlay = False
        GLib.idle_add(self.show_overlay, False)

    def _on_loading_changed(self, player, status, track_id):
        """
            Show a spinner while loading
            @param player as Player
            @param status as bool
            @param track_id as int
        """
        if status and not self._show_overlay:
            return
        if status:
            if self._spinner is None:
                self._spinner = Gtk.Spinner()
                self._spinner.show()
                self._spinner.start()
                style_context = self._spinner.get_style_context()
                style_context.add_class("black-transparent")
                self._overlay.add_overlay(self._spinner)
        else:
            if self._spinner is not None:
                self._spinner.destroy()
                self._spinner = None

#######################
# PRIVATE             #
#######################
    def __on_unmap(self, widget):
        """
            Disconnect player signals
            @param widget as Gtk.Widget
        """
        if self.__loading_changed_id is not None:
            App().player.disconnect(self.__loading_changed_id)
            self.__loading_changed_id = None
