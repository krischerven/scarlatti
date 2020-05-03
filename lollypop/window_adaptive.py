# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GObject, Gtk, GLib

from lollypop.utils import emit_signal
from lollypop.define import AdaptiveSize, Size


class AdaptiveWindow:
    """
        Handle window resizing and window's children workflow
        This class needs a stack and n paned
    """

    gsignals = {
        "adaptive-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "adaptive-size-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }
    for signal in gsignals:
        args = gsignals[signal]
        GObject.signal_new(signal, Gtk.Window,
                           args[0], args[1], args[2])

    def __init__(self):
        """
            Init adaptive mode, Gtk.Window should be initialised
        """
        self.__is_adaptive = None
        self.__configure_timeout_id = None
        self.__adaptive_size = AdaptiveSize.NONE
        self.connect("configure-event", self.__on_configure_event)

    def set_adaptive(self, is_adaptive):
        """
            Handle adaptive switch
            @param is_adaptive as bool
        """
        if is_adaptive != self.__is_adaptive:
            self.__is_adaptive = is_adaptive
            emit_signal(self, "adaptive-changed", is_adaptive)

    @property
    def adaptive_size(self):
        """
            Get adaptive size
            @return AdaptiveSize
        """
        return self.__adaptive_size

    @property
    def is_adaptive(self):
        """
            True if adaptive is on
            @return bool
        """
        return False if self.__is_adaptive is None else self.__is_adaptive

#############
# PROTECTED #
#############
    def _on_configure_event_timeout(self, width, height, x, y):
        """
            Handle adaptive mode
            @param width as int
            @param height as int
            @param x as int
            @param y as int
        """
        self.__configure_timeout_id = None
        if width <= Size.MEDIUM:
            self.set_adaptive(True)
        else:
            self.set_adaptive(False)
        if width <= Size.PHONE:
            adaptive_size = AdaptiveSize.PHONE
        if width <= Size.SMALL:
            adaptive_size = AdaptiveSize.SMALL
        elif width <= Size.MEDIUM:
            adaptive_size = AdaptiveSize.MEDIUM
        elif width <= Size.NORMAL:
            adaptive_size = AdaptiveSize.NORMAL
        elif width <= Size.BIG:
            adaptive_size = AdaptiveSize.BIG
        else:
            adaptive_size = AdaptiveSize.LARGE
        if adaptive_size != self.__adaptive_size:
            self.__adaptive_size = adaptive_size
            emit_signal(self, "adaptive-size-changed", adaptive_size)

############
# PRIVATE  #
############
    def __on_configure_event(self, window, event):
        """
            Delay event
            @param window as Gtk.Window
            @param event as Gdk.EventConfigure
        """
        if self.__configure_timeout_id:
            GLib.source_remove(self.__configure_timeout_id)
        (width, height) = window.get_size()
        (x, y) = window.get_position()
        self.__configure_timeout_id = GLib.idle_add(
            self._on_configure_event_timeout,
            width, height, x, y, priority=GLib.PRIORITY_LOW)
