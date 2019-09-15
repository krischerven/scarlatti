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

from gi.repository import Gtk, Gdk, GObject, GLib

from lollypop.define import ArtSize, ViewType, MARGIN, App
from lollypop.helper_size_allocation import SizeAllocationHelper


class Overlay(Gtk.Overlay):
    """
        Overlay with constraint size
    """
    def __init__(self, banner):
        """
            Init overlay
            @param banner as BannerWidget
        """
        Gtk.Overlay.__init__(self)
        self.__banner = banner

    def do_get_preferred_width(self):
        """
            Force preferred width
        """
        (min, nat) = Gtk.Bin.do_get_preferred_width(self)
        # Allow resizing
        return (0, 0)

    def do_get_preferred_height(self):
        """
           Force preferred height
        """
        height = self.__banner.height
        return (height, height)


class BannerWidget(Gtk.Revealer, SizeAllocationHelper):
    """
        Default banner widget
    """

    gsignals = {
        "scroll": (GObject.SignalFlags.RUN_FIRST, None, (float, float))
    }
    for signal in gsignals:
        args = gsignals[signal]
        GObject.signal_new(signal, Gtk.Revealer,
                           args[0], args[1], args[2])

    def __init__(self, view_type):
        """
            Init bannner
            @param view_type as ViewType
        """
        Gtk.Revealer.__init__(self)
        self.__scroll_timeout_id = None
        self._view_type = view_type
        self.set_property("valign", Gtk.Align.START)
        self.get_style_context().add_class("black")
        self._overlay = Overlay(self)
        self._overlay.show()
        self._artwork = Gtk.Image()
        self._artwork.show()
        if App().animations:
            SizeAllocationHelper.__init__(self)
            self._artwork.get_style_context().add_class("black")
            self._artwork.set_opacity(0.99)
        else:
            self._artwork.get_style_context().add_class("default-banner")
        eventbox = Gtk.EventBox.new()
        eventbox.show()
        eventbox.add_events(Gdk.EventMask.ALL_EVENTS_MASK)
        eventbox.add(self._artwork)
        self._overlay.add(eventbox)
        self.__event_controller = Gtk.EventControllerScroll.new(
            eventbox, Gtk.EventControllerScrollFlags.BOTH_AXES)
        self.__event_controller.set_propagation_phase(
            Gtk.PropagationPhase.TARGET)
        self.__event_controller.connect("scroll", self.__on_scroll)
        self.add(self._overlay)
        self.set_reveal_child(True)
        self.set_transition_duration(250)

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        self._view_type = view_type

    @property
    def height(self):
        """
            Get wanted height
            @return int
        """
        if self._view_type & (ViewType.ADAPTIVE | ViewType.SMALL):
            return ArtSize.MEDIUM + MARGIN * 2
        else:
            return ArtSize.BANNER + MARGIN * 2

#######################
# PROTECTED           #
#######################
    def _on_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is not None:
            self._artwork.set_from_surface(surface)
        else:
            self._artwork.get_style_context().add_class("default-banner")

#######################
# PRIVATE             #
#######################
    def __on_scroll(self, event_controller, x, y):
        """
            Pass scroll
            @param event_controller as Gtk.EventControllerScroll
            @param x as int
            @param y as int
        """
        def emit_scroll(x, y):
            self.__scroll_timeout_id = None
            self.emit("scroll", x, y)

        if self.__scroll_timeout_id is not None:
            GLib.source_remove(self.__scroll_timeout_id)
        self.__scroll_timeout_id = GLib.timeout_add(10, emit_scroll, x, y)
