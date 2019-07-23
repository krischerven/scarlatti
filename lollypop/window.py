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

from gi.repository import Gtk, Gdk, GLib

from lollypop.define import App, Sizing, ScanType
from lollypop.toolbar import Toolbar
from lollypop.adaptive import AdaptiveWindow
from lollypop.utils import is_unity, get_headerbar_buttons_width
from lollypop.helper_signals import SignalsHelper, signals_map


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
        self.__timeout = None
        self.__miniplayer = None
        self.__headerbar_buttons_width = get_headerbar_buttons_width()
        App().player.connect("current-changed", self.__on_current_changed)
        self.__timeout_configure_id = None
        self.__setup_content()
        self.set_auto_startup_notification(False)
        self.connect("realize", self.__on_realize)
        self.__multi_press = Gtk.GestureMultiPress.new(self)
        self.__multi_press.set_propagation_phase(Gtk.PropagationPhase.TARGET)
        self.__multi_press.connect("released", self.__on_back_button_clicked)
        self.__multi_press.set_button(8)
        return [
            (self, "window-state-event", "_on_window_state_event"),
            (self, "configure-event", "_on_configure_event")
        ]

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
    def _on_configure_event(self, window, event):
        """
            Handle configure event
            @param window as Gtk.Window
            @param event as Gdk.Event
        """
        def on_configure_event(width, height):
            self.__timeout_configure_id = None
            self.__handle_miniplayer(width, height)
            self.__toolbar.set_content_width(width)
            self.__save_size_position(window)

        (width, height) = window.get_size()
        if self.__timeout_configure_id:
            GLib.source_remove(self.__timeout_configure_id)
            self.__timeout_configure_id = None
        self.__timeout_configure_id = GLib.idle_add(on_configure_event,
                                                    width, height,
                                                    priority=GLib.PRIORITY_LOW)

    def _on_window_state_event(self, widget, event):
        """
            Save maximised state
        """
        App().settings.set_boolean("window-maximized",
                                   "GDK_WINDOW_STATE_MAXIMIZED" in
                                   event.new_window_state.value_names)

############
# PRIVATE  #
############
    def __setup_size_and_position(self):
        """
            Setup window position and size, callbacks
        """
        size = App().settings.get_value("window-size")
        pos = App().settings.get_value("window-position")
        self.__setup_size(size)
        self.__setup_pos(pos)
        if App().settings.get_value("window-maximized"):
            # Lets resize happen
            GLib.idle_add(self.maximize)
            self.do_adaptive_mode(self._ADAPTIVE_STACK)
        else:
            self.do_adaptive_mode(size[0])

    def __show_miniplayer(self, show):
        """
            Show/hide subtoolbar
            @param show as bool
        """
        def on_revealed(miniplayer, revealed):
            miniplayer.set_vexpand(revealed)
            if revealed:
                self.__container.hide()
                self.emit("can-go-back-changed", False)
                self.toolbar.end.home_button.set_sensitive(False)
            else:
                self.__container.show()
                self.emit("can-go-back-changed", self.can_go_back)
                self.toolbar.end.home_button.set_sensitive(True)
        if show and self.__miniplayer is None:
            from lollypop.miniplayer import MiniPlayer
            self.__miniplayer = MiniPlayer()
            self.__miniplayer.connect("revealed", on_revealed)
            self.__miniplayer.set_vexpand(False)
            self.__vgrid.add(self.__miniplayer)
            self.__toolbar.set_mini(True)
        elif not show and self.__miniplayer is not None:
            self.__toolbar.set_mini(False)
            self.__miniplayer.destroy()
            self.__miniplayer = None

    def __setup_size(self, size):
        """
            Set window size
            @param size as (int, int)
        """
        if len(size) == 2 and\
           isinstance(size[0], int) and\
           isinstance(size[1], int):
            self.resize(size[0], size[1])

    def __setup_pos(self, pos):
        """
            Set window position
            @param pos as (int, int)
        """
        if len(pos) == 2 and\
           isinstance(pos[0], int) and\
           isinstance(pos[1], int):
            self.move(pos[0], pos[1])

    def __setup_content(self):
        """
            Setup window content
        """
        self.__vgrid = Gtk.Grid()
        self.__vgrid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__vgrid.show()
        self.__toolbar = Toolbar(self)
        self.__toolbar.show()
        if App().settings.get_value("disable-csd") or is_unity():
            self.__vgrid.add(self.__toolbar)
        else:
            self.set_titlebar(self.__toolbar)
            self.__toolbar.set_show_close_button(
                not App().settings.get_value("disable-csd"))
        self.add(self.__vgrid)
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self.__on_drag_data_received)

    def __handle_miniplayer(self, width, height):
        """
            Handle mini player show/hide
            @param width as int
            @param height as int
        """
        if width - self.__headerbar_buttons_width < Sizing.MPRIS:
            self.__show_miniplayer(True)
        else:
            self.__show_miniplayer(False)
            self.__container.show()

    def __save_size_position(self, widget):
        """
            Save window state, update current view content size
            @param: widget as Gtk.Window
        """
        if self.is_maximized():
            return
        (width, height) = widget.get_size()
        # Keep a minimal height
        if height < Sizing.MEDIUM:
            height = Sizing.MEDIUM
        App().settings.set_value("window-size",
                                 GLib.Variant("ai", [width, height]))
        (x, y) = widget.get_position()
        App().settings.set_value("window-position", GLib.Variant("ai", [x, y]))

    def __on_realize(self, widget):
        """
            Run scanner on realize
            @param widget as Gtk.Widget
        """
        from lollypop.container import Container
        self.__container = Container()
        self.set_stack(self.container.stack)
        self.__container.show()
        self.__vgrid.add(self.__container)
        self.__container.setup_lists()
        self.__setup_size_and_position()
        if App().settings.get_value("auto-update") or App().tracks.is_empty():
            # Delayed, make python segfault on sys.exit() otherwise
            # No idea why, maybe scanner using Gstpbutils before Gstreamer
            # initialisation is finished...
            GLib.timeout_add(1000, App().scanner.update, ScanType.FULL)
        # Here we ignore initial configure events
        self.__toolbar.set_content_width(self.get_size()[0])

    def __on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        if App().player.current_track.id is None:
            self.set_title("Lollypop")
        else:
            artists = ", ".join(player.current_track.artists)
            self.set_title("%s - %s" % (artists, "Lollypop"))

    def __on_back_button_clicked(self, gesture, n_press, x, y):
        """
            Handle special mouse buttons
            @param gesture as Gtk.Gesture
            @param n_press as int
            @param x as int
            @param y as int
        """
        App().window.go_back()

    def __on_drag_data_received(self, widget, context, x, y, data, info, time):
        """
            Import values
            @param widget as Gtk.Widget
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        try:
            from lollypop.collectionimporter import CollectionImporter
            from urllib.parse import urlparse
            importer = CollectionImporter()
            uris = []
            for uri in data.get_text().strip("\n").split("\r"):
                parsed = urlparse(uri)
                if parsed.scheme in ["file", "sftp", "smb", "webdav"]:
                    uris.append(uri)
            if uris:
                App().task_helper.run(importer.add, uris,
                                      callback=(App().scanner.update,))
        except:
            pass
