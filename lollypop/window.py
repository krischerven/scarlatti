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

from gi.repository import Gtk, Gio, Gdk, GLib

from gettext import gettext as _

from lollypop.container import Container
from lollypop.define import App, Sizing, Type, ScanType
from lollypop.toolbar import Toolbar
from lollypop.logger import Logger
from lollypop.adaptive import AdaptiveWindow
from lollypop.utils import is_unity, get_headerbar_buttons_width


class Window(Gtk.ApplicationWindow, AdaptiveWindow):
    """
        Main window
    """

    def __init__(self):
        """
            Init window
        """
        Gtk.ApplicationWindow.__init__(self,
                                       application=App(),
                                       title="Lollypop",
                                       icon_name="org.gnome.Lollypop")
        AdaptiveWindow.__init__(self)
        self.__signal1 = None
        self.__signal2 = None
        self.__timeout = None
        self.__miniplayer = None
        self.__mediakeys = None
        self.__sidebar_shown = False
        self.__media_keys_busnames = []
        self.__headerbar_buttons_width = get_headerbar_buttons_width()
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        App().player.connect("current-changed", self.__on_current_changed)
        self.__timeout_configure = None

        self.__setup_content()

        # FIXME Remove this, handled by MPRIS in GNOME 3.26
        self.__setup_media_keys()
        self.set_auto_startup_notification(False)
        self.connect("realize", self.__on_realize)
        self.connect("adaptive-changed", self.__on_adaptive_changed)
        self.connect("button-release-event", self.__on_button_release_event)
        self.connect("focus-out-event", self.__on_focus_out_event)

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

############
# PRIVATE  #
############
    def __setup(self):
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

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __setup_media_keys(self):
        """
            Setup media player keys
        """
        self.__media_keys_busnames = [
            "org.gnome.SettingDaemon.MediaKeys",
            "org.gnome.SettingsDaemon",
        ]

        self.__get_media_keys_proxy()

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __get_media_keys_proxy(self):
        if self.__media_keys_busnames:
            bus_name = self.__media_keys_busnames.pop(0)
            try:
                bus = App().get_dbus_connection()
                Gio.DBusProxy.new(
                    bus,
                    Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                    None,
                    bus_name,
                    "/org/gnome/SettingsDaemon/MediaKeys",
                    "org.gnome.SettingsDaemon.MediaKeys",
                    None,
                    self.__on_get_proxy,
                )

            except Exception as e:
                Logger.error("Window::__setup_media_keys(): %s" % e)

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __on_get_proxy(self, source, result):
        try:
            self.__mediakeys = source.new_finish(result)
        except Exception as e:
            self.__mediakeys = None
            Logger.error("Window::__on_get_proxy(): %s" % e)
        else:
            if self.__mediakeys.get_name_owner():
                self.__grab_media_keys()
                self.__mediakeys.connect('g-signal', self.__mediakey_signal)
            else:
                self.__mediakeys = None
                self.__get_media_keys_proxy()

    # FIXME Remove this, handled by MPRIS in GNOME 3.26
    def __grab_media_keys(self):
        if not self.__mediakeys:
            return
        self.__mediakeys.call(
            "GrabMediaPlayerKeys",
            GLib.Variant("(su)", ("org.gnome.Lollypop", 0)),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None,
        )

    def __mediakey_signal(self, proxy, sender, signal, param, userdata=None):
        if signal != "MediaPlayerKeyPressed":
            return

        app, action = param.unpack()
        if app == "org.gnome.Lollypop":
            if action == "Play":
                App().player.play_pause()
            elif action == "Next":
                App().player.next()
            elif action == "Stop":
                App().player.stop()
            elif action == "Previous":
                App().player.prev()

    def __setup_content(self):
        """
            Setup window content
        """
        self.__container = Container()
        self.set_stack(self.container.stack)
        self.__container.show()
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
        self.__vgrid.add(self.__container)
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
        if width - self.__headerbar_buttons_width < Sizing.MONSTER:
            self.__show_miniplayer(True)
        else:
            self.__show_miniplayer(False)
            self.__container.show()

    def __show_sidebar(self, show):
        """
            Show sidebar if needed
            @param show as bool
        """
        if self.__sidebar_shown:
            return
        self.__sidebar_shown = True
        self.__container.show_sidebar(show)

    def __save_size_position(self, widget):
        """
            Save window state, update current view content size
            @param: widget as Gtk.Window
        """
        self.__timeout_configure = None
        (width, height) = widget.get_size()
        # Keep a minimal height
        if height < Sizing.MEDIUM:
            height = Sizing.MEDIUM
        App().settings.set_value("window-size",
                                 GLib.Variant("ai", [width, height]))
        (x, y) = widget.get_position()
        App().settings.set_value("window-position", GLib.Variant("ai", [x, y]))

    def __on_window_state_event(self, widget, event):
        """
            Save maximised state
        """
        App().settings.set_boolean("window-maximized",
                                   "GDK_WINDOW_STATE_MAXIMIZED" in
                                   event.new_window_state.value_names)
        if event.changed_mask & Gdk.WindowState.FOCUSED and \
           event.new_window_state & Gdk.WindowState.FOCUSED:
            # FIXME Remove this, handled by MPRIS in GNOME 3.26
            self.__grab_media_keys()

    def __on_realize(self, widget):
        """
            Run scanner on realize
            @param widget as Gtk.Widget
        """
        self.__setup()
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

    def __on_focus_out_event(self, window, event):
        """
            Disable overlay on children
            @param window as Gtk.Window
            @param event as Gdk.EventFocus
        """
        if self.__container.view is not None:
            self.__container.view.disable_overlay()

    def __on_button_release_event(self, window, event):
        """
            Handle special mouse buttons
            @param window as Gtk.Window
            @param event as Gdk.EventButton
        """
        if event.button == 8:
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

    def __on_map(self, window):
        """
            Connect signals
            @param window as Window
        """
        if self.__signal1 is None:
            self.__signal1 = self.connect("window-state-event",
                                          self.__on_window_state_event)
        if self.__signal2 is None:
            self.__signal2 = self.connect("configure-event",
                                          self.__on_configure_event)

    def __on_unmap(self, window):
        """
            Disconnect signals
            @param window as Window
        """
        if self.__signal1 is not None:
            self.disconnect(self.__signal1)
            self.__signal1 = None
        if self.__signal2 is not None:
            self.disconnect(self.__signal2)
            self.__signal2 = None

    def __on_configure_event(self, window, event):
        """
            Handle configure event
            @param window as Gtk.Window
            @param event as Gdk.Event
        """
        (width, height) = window.get_size()
        self.__handle_miniplayer(width, height)
        self.__toolbar.set_content_width(width)
        if self.__timeout_configure:
            GLib.source_remove(self.__timeout_configure)
            self.__timeout_configure = None
        if not self.is_maximized():
            self.__timeout_configure = GLib.timeout_add(
                1000,
                self.__save_size_position,
                window)

    def __on_adaptive_changed(self, window, adaptive_stack):
        """
            Handle adaptive mode
            @param window as AdaptiveWindow
            @param adaptive_stack as bool
        """
        show_sidebar = App().settings.get_value("show-sidebar")
        self.__show_sidebar(show_sidebar)
        if show_sidebar:
            widget = self.__container.list_one
        else:
            widget = self.__container.rounded_artists_view
        if adaptive_stack:
            self.__toolbar.end.set_mini(True)
            widget.add_value((Type.SEARCH, _("Search"), _("Search")))
            widget.add_value((Type.CURRENT,
                              _("Current playlist"),
                              _("Current playlist")))
            self.emit("show-can-go-back", True)
        else:
            self.__toolbar.end.set_mini(False)
            widget.remove_value(Type.CURRENT)
            widget.remove_value(Type.SEARCH)
            if App().settings.get_value("show-sidebar"):
                self.emit("show-can-go-back", False)
        self.emit("can-go-back-changed", self.can_go_back)
