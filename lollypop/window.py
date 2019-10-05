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

from lollypop.define import App, ScanType, AdaptiveSize
from lollypop.container import Container
from lollypop.toolbar import Toolbar
from lollypop.adaptive import AdaptiveWindow
from lollypop.utils import is_unity, emit_signal
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.logger import Logger


class Window(Gtk.ApplicationWindow, AdaptiveWindow, SignalsHelper):
    """
        Main window
    """

    @signals_map
    def __init__(self):
        """
            Init window
        """
        Gtk.ApplicationWindow.__init__(self,
                                       application=App(),
                                       title="Lollypop",
                                       icon_name="org.gnome.Lollypop")
        AdaptiveWindow.__init__(self)
        self.__miniplayer = None
        self.set_auto_startup_notification(False)
        self.connect("realize", self.__on_realize)
        self.__multi_press = Gtk.GestureMultiPress.new(self)
        self.__multi_press.set_propagation_phase(Gtk.PropagationPhase.TARGET)
        self.__multi_press.connect("released", self.__on_back_button_clicked)
        self.__multi_press.set_button(8)
        self.connect("window-state-event", self.__on_window_state_event)
        self.connect("adaptive-size-changed", self.__on_adaptive_size_changed)
        return [
            (App().player, "current-changed", "_on_current_changed")
        ]

    def setup(self):
        """
            Setup window content
        """
        self.__vgrid = Gtk.Grid()
        self.__vgrid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__vgrid.show()
        self.__container = Container()
        self.__container.show()
        self.__container.setup_lists()
        self.__toolbar = Toolbar(self)
        self.__toolbar.show()
        if App().settings.get_value("disable-csd") or is_unity():
            self.__vgrid.add(self.__toolbar)
        else:
            self.set_titlebar(self.__toolbar)
            self.__toolbar.set_show_close_button(
                not App().settings.get_value("disable-csd"))
        self.__vgrid.add(self.__container)
        self.add(self.__vgrid)

    @property
    def miniplayer(self):
        """
            True if miniplayer is on
            @return bool
        """
        return self.__miniplayer is not None

    @property
    def toolbar(self):
        """
            toolbar as Toolbar
        """
        return self.__toolbar

    @property
    def container(self):
        """
            Get container
            @return Container
        """
        return self.__container

##############
# PROTECTED  #
##############
    def _on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        if App().player.current_track.id is None:
            self.set_title("Lollypop")
        else:
            artists = ", ".join(player.current_track.artists)
            self.set_title("%s - %s" % (artists, player.current_track.name))
            if self.__miniplayer is not None:
                self.__miniplayer.show()

    def _on_configure_event_timeout(self, width, height, x, y):
        """
            Setup content based on current size
            @param width as int
            @param height as int
            @param x as int
            @param y as int
        """
        AdaptiveWindow._on_configure_event_timeout(self, width, height, x, y)
        if not self.is_maximized():
            # Keep a minimal height
            if height < AdaptiveSize.SMALL:
                height = AdaptiveSize.SMALL
            App().settings.set_value("window-size",
                                     GLib.Variant("ai", [width, height]))
        App().settings.set_value("window-position", GLib.Variant("ai", [x, y]))

############
# PRIVATE  #
############
    def __setup_size_and_position(self):
        """
            Setup window position and size, callbacks
        """
        try:
            size = App().settings.get_value("window-size")
            pos = App().settings.get_value("window-position")
            self.resize(size[0], size[1])
            self.move(pos[0], pos[1])
            if App().settings.get_value("window-maximized"):
                # Lets resize happen
                GLib.idle_add(self.maximize)
                self.set_adaptive(False)
            else:
                AdaptiveWindow._on_configure_event_timeout(
                    self, size[0], size[1], pos[0], pos[1])
        except Exception as e:
            Logger.error("Window::__setup_size_and_position(): %s", e)

    def __show_miniplayer(self, show):
        """
            Show/hide subtoolbar
            @param show as bool
        """
        def on_revealed(miniplayer, revealed):
            miniplayer.set_vexpand(revealed)
            if revealed:
                self.__container.hide()
                emit_signal(self.__container, "can-go-back-changed", False)
                self.toolbar.end.home_button.set_sensitive(False)
            else:
                self.__container.show()
                emit_signal(self.__container, "can-go-back-changed",
                            self.__container.can_go_back)
                self.toolbar.end.home_button.set_sensitive(True)
        if show and self.__miniplayer is None:
            from lollypop.miniplayer import MiniPlayer
            self.__miniplayer = MiniPlayer()
            if App().player.current_track.id is not None:
                self.__miniplayer.show()
            self.__miniplayer.connect("revealed", on_revealed)
            self.__miniplayer.set_vexpand(False)
            self.__vgrid.add(self.__miniplayer)
        elif not show and self.__miniplayer is not None:
            self.__miniplayer.destroy()
            self.__miniplayer = None
            self.__container.show()

    def __on_realize(self, window):
        """
            Init window content
            @param window as Gtk.Window
        """
        self.__setup_size_and_position()
        if App().settings.get_value("auto-update") or App().tracks.is_empty():
            # Delayed, make python segfault on sys.exit() otherwise
            # No idea why, maybe scanner using Gstpbutils before Gstreamer
            # initialisation is finished...
            GLib.timeout_add(1000, App().scanner.update, ScanType.FULL)

    def __on_back_button_clicked(self, gesture, n_press, x, y):
        """
            Handle special mouse buttons
            @param gesture as Gtk.Gesture
            @param n_press as int
            @param x as int
            @param y as int
        """
        App().window.go_back()

    def __on_window_state_event(self, widget, event):
        """
            Save maximised state
        """
        App().settings.set_boolean("window-maximized",
                                   "GDK_WINDOW_STATE_MAXIMIZED" in
                                   event.new_window_state.value_names)

    def __on_adaptive_size_changed(self, window, adaptive_size):
        """
            show/hide miniplayer
            @param window as Gtk.Window
            @param adaptive_size as AdaptiveSize
        """
        self.__show_miniplayer(adaptive_size & (AdaptiveSize.SMALL |
                                                AdaptiveSize.MEDIUM |
                                                AdaptiveSize.NORMAL))
