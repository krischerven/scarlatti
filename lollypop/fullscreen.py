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

from gi.repository import Gtk, Gdk, GLib, Gio, Gst

from datetime import datetime
from gettext import gettext as _

from lollypop.define import App, ArtSize, ArtBehaviour, Type, ViewType
from lollypop.controller_information import InformationController
from lollypop.controller_playback import PlaybackController
from lollypop.controller_progress import ProgressController
from lollypop.container import Container
from lollypop.adaptive import AdaptiveWindow
from lollypop.logger import Logger


class FullScreen(Gtk.Window, AdaptiveWindow, InformationController,
                 PlaybackController, ProgressController):
    """
        Show a fullscreen window showing current track context
    """

    def __init__(self, app):
        """
            Init window for app
            @param app as Gio.Application
        """
        Gtk.Window.__init__(self)
        AdaptiveWindow.__init__(self)
        self.get_style_context().add_class("black")
        self.set_title("Lollypop")
        self.__allocation = Gdk.Rectangle()
        PlaybackController.__init__(self)
        ProgressController.__init__(self)
        self.set_application(app)
        self.__timeout_id = None
        self.__signal1_id = self.__signal2_id = None
        self.set_decorated(False)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/FullScreen.ui")
        builder.connect_signals(self)

        # Calculate cover size
        screen = Gdk.Screen.get_default()
        monitor = screen.get_monitor_at_window(App().main_window.get_window())
        geometry = screen.get_monitor_geometry(monitor)
        self.__overlay_grid = builder.get_object("overlay_grid")
        art_size_fs = ArtSize.FULLSCREEN / self.get_scale_factor()
        font_size_fs = 11 / self.get_scale_factor()
        if geometry.width > geometry.height:
            self.__art_size = int(art_size_fs * geometry.height / 1080)
            self.__font_size = int(font_size_fs * geometry.height / 1080)
        else:
            self.__art_size = int(art_size_fs * geometry.width / 1920)
            self.__font_size = int(font_size_fs * geometry.width / 1920)
        widget = builder.get_object("widget")
        self._play_button = builder.get_object("play_btn")
        self._next_button = builder.get_object("next_btn")
        self._prev_button = builder.get_object("prev_btn")
        if App().player.current_track.id == Type.RADIOS:
            self._next_button.hide()
            self._prev_button.hide()
        self._play_image = builder.get_object("play_image")
        self._pause_image = builder.get_object("pause_image")
        close_btn = builder.get_object("close_btn")
        preferences = Gio.Settings.new("org.gnome.desktop.wm.preferences")
        layout = preferences.get_value("button-layout").get_string()
        if layout.split(":")[0] == "close":
            self.__overlay_grid.attach(close_btn, 0, 0, 1, 1)
            close_btn.set_property("halign", Gtk.Align.START)
        else:
            self.__overlay_grid.attach(close_btn, 2, 0, 1, 1)
            close_btn.set_property("halign", Gtk.Align.END)
        self._artwork = builder.get_object("cover")
        self.__setup_controller()
        self._title_label = builder.get_object("title")
        self._artist_label = builder.get_object("artist")
        self._album_label = builder.get_object("album")
        self.__revealer = builder.get_object("revealer")
        self._datetime = builder.get_object("datetime")
        self._progress = builder.get_object("progress_scale")
        self._timelabel = builder.get_object("playback")
        self._total_time_label = builder.get_object("duration")
        self.connect("key-release-event", self.__on_key_release_event)

        # Add a navigation widget on the right
        self.__back_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.__back_button.set_sensitive(False)
        self.__back_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__back_button.set_property("valign", Gtk.Align.START)
        self.__back_button.set_property("halign", Gtk.Align.START)
        self.__back_button.connect("clicked", self.__on_back_button_clicked)
        self.__back_button.set_margin_start(5)
        self.__back_button.set_margin_end(5)
        self.__back_button.set_margin_top(5)
        self.__back_button.set_margin_bottom(5)
        self.__back_button.show()
        self.__background_artwork = builder.get_object("background_artwork")
        self.__container = Container(ViewType.NOT_ADAPTIVE)
        self.set_stack(self.__container.stack)
        self.__container.show()
        self.__sidebar = Gtk.Grid()
        self.__sidebar.set_size_request(400, -1)
        self.__sidebar.set_orientation(Gtk.Orientation.VERTICAL)
        self.__sidebar.get_style_context().add_class("borders-left-top")
        self.__sidebar.show()
        self.__sidebar.add(self.__back_button)
        self.__sidebar.add(self.__container)
        self.__sidebar.set_size_request(450, -1)
        self.connect("can-go-back-changed", self.__on_can_go_back_changed)
        self.connect("show-can-go-back", self.__on_show_can_go_back)
        self.connect("size-allocate", self.__on_size_allocate)
        self.__sidebar.get_style_context().add_class("background-opacity")
        self.__revealer.add(self.__sidebar)
        self.add(widget)

    def do_show(self):
        """
            Setup window for current screen
        """
        show_sidebar = App().settings.get_value("show-sidebar")
        self.__container.show_sidebar(show_sidebar)
        self.__signal1_id = App().player.connect("current-changed",
                                                 self.on_current_changed)
        self.__signal2_id = App().player.connect("status-changed",
                                                 self.on_status_changed)
        self.on_status_changed(App().player)
        self.on_current_changed(App().player)
        Gtk.Window.do_show(self)
        if self.__timeout_id is None:
            try:
                interface = Gio.Settings.new("org.gnome.desktop.interface")
                show_seconds = interface.get_value("clock-show-seconds")
            except:
                show_seconds = False
            self.__update_datetime(show_seconds)
            self.__timeout_id = GLib.timeout_add(1000,
                                                 self.__update_datetime,
                                                 show_seconds)
        self.update_position(App().player.position / Gst.SECOND)
        screen = Gdk.Screen.get_default()
        monitor = screen.get_monitor_at_window(App().main_window.get_window())
        self.fullscreen_on_monitor(screen, monitor)

        # Disable screensaver (idle)
        App().inhibitor.manual_inhibit(
                Gtk.ApplicationInhibitFlags.IDLE |
                Gtk.ApplicationInhibitFlags.SUSPEND)

    def do_hide(self):
        """
            Clean window
        """
        Gtk.Window.do_hide(self)
        if self.__signal1_id is not None:
            App().player.disconnect(self.__signal1_id)
            self.__signal1_id = None
        if self.__signal2_id is not None:
            App().player.disconnect(self.__signal2_id)
            self.__signal2_id = None
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        App().inhibitor.manual_uninhibit()
        ProgressController.on_destroy(self)

    def on_status_changed(self, player):
        """
            Update controller
            @param player as Player
        """
        ProgressController.on_status_changed(self, player)
        PlaybackController.on_status_changed(self, player)

    def on_current_changed(self, player):
        """
            Update controllers
            @param player as Player
        """
        InformationController.on_current_changed(self,
                                                 self.__art_size,
                                                 self.__font_size)
        ProgressController.on_current_changed(self, player)
        self.__update_background()
        if player.current_track.id is not None:
            album_name = player.current_track.album.name
            if player.current_track.year:
                album_name += " (%s)" % player.current_track.year
            self._album_label.set_markup(
                "<span font='%s'>%s</span>" %
                                        (self.__font_size - 1,
                                         GLib.markup_escape_text(album_name)))

    @property
    def miniplayer(self):
        return App().main_window.miniplayer

    @property
    def toolbar(self):
        return App().main_window.toolbar

    @property
    def is_adaptive(self):
        return True

    @property
    def container(self):
        """
            Get container
            @return Container
        """
        return self.__container

#######################
# PROTECTED           #
#######################
    def _on_artwork(self, surface):
        """
            Set artwork
            @param surface as str
        """
        if surface is None:
            if App().player.current_track.id == Type.RADIOS:
                icon_name = "audio-input-microphone-symbolic"
            else:
                icon_name = "folder-music-symbolic"
            self._artwork.set_from_icon_name(icon_name,
                                             Gtk.IconSize.DIALOG)
            self._artwork.set_size_request(self.__art_size, self.__art_size)
        else:
            InformationController._on_artwork(self, surface)
            self._artwork.set_size_request(-1, -1)

    def _on_close_button_clicked(self, button):
        """
            Destroy self
            @param button as Gtk.Button
        """
        self.destroy()

    def _on_reveal_button_clicked(self, button):
        """
            Reveal widget
            @param button as Gtk.Button
        """
        if self.__revealer.get_reveal_child():
            self.__revealer.set_reveal_child(False)
            button.get_image().set_from_icon_name("pan-start-symbolic",
                                                  Gtk.IconSize.BUTTON)
        else:
            self.set_adaptive_stack(True)
            self.__revealer.set_reveal_child(True)
            button.get_image().set_from_icon_name("pan-end-symbolic",
                                                  Gtk.IconSize.BUTTON)

    def _on_image_realize(self, eventbox):
        """
            Set cursor
            @param eventbox as Gtk.EventBox
        """
        try:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

    def _on_image_button_release_event(self, widget, event):
        """
            Change artwork type
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        fs_type = App().settings.get_value("fullscreen-type").get_int32()
        if fs_type & ArtBehaviour.BLUR_HARD and\
                fs_type & ArtBehaviour.ROUNDED:
            fs_type = ArtBehaviour.NONE
        elif fs_type & ArtBehaviour.NONE:
            fs_type = ArtBehaviour.BLUR_HARD
        elif fs_type & ArtBehaviour.BLUR_HARD:
            fs_type |= ArtBehaviour.ROUNDED
            fs_type &= ~ArtBehaviour.BLUR_HARD
        elif fs_type & ArtBehaviour.ROUNDED:
            fs_type |= ArtBehaviour.BLUR_HARD
        else:
            fs_type = ArtBehaviour.NONE
        App().settings.set_value("fullscreen-type",
                                 GLib.Variant("i", fs_type))
        self.__setup_controller()
        self.__update_background()
        InformationController.on_current_changed(self,
                                                 self.__art_size,
                                                 self.__font_size)

#######################
# PRIVATE             #
#######################
    def __setup_controller(self):
        """
            Setup controller
        """
        fs_type = App().settings.get_value("fullscreen-type").get_int32()
        context = self._artwork.get_style_context()
        behaviour = ArtBehaviour.CROP_SQUARE
        if fs_type & ArtBehaviour.ROUNDED:
            context.add_class("image-rotate")
            context.remove_class("cover-frame")
            behaviour |= ArtBehaviour.ROUNDED
        else:
            context.remove_class("image-rotate")
            context.add_class("cover-frame")
        InformationController.__init__(self, False, behaviour)

    def __update_background(self, album_artwork=False):
        """
            Update window background
            @param album_artwork as bool
        """
        try:
            if App().player.current_track.id is None:
                return
            allocation = self.get_allocation()
            if allocation.width <= 1 or allocation.height <= 1:
                return
            behaviour = App().settings.get_value("fullscreen-type").get_int32()
            behaviour |= (ArtBehaviour.CROP | ArtBehaviour.DARKER)
            # We don't want this for background, stored for album cover
            behaviour &= ~ArtBehaviour.ROUNDED
            if App().player.current_track.id == Type.RADIOS:
                App().art_helper.set_radio_artwork(
                                    App().player.current_track.radio_name,
                                    allocation.width,
                                    allocation.height,
                                    self.get_scale_factor(),
                                    behaviour | ArtBehaviour.BLUR_MAX,
                                    self.__on_artwork,
                                    False)
            elif not album_artwork and\
                    App().settings.get_value("artist-artwork"):
                if App().player.current_track.album.artists:
                    artist = App().player.current_track.album.artists[0]
                else:
                    artist = App().player.current_track.artists[0]
                App().art_helper.set_artist_artwork(
                                    artist,
                                    allocation.width,
                                    allocation.height,
                                    self.get_scale_factor(),
                                    behaviour,
                                    self.__on_artwork,
                                    False)
            else:
                App().art_helper.set_album_artwork(
                                    App().player.current_track.album,
                                    allocation.width,
                                    allocation.height,
                                    self.get_scale_factor(),
                                    behaviour | ArtBehaviour.BLUR_MAX,
                                    self.__on_artwork,
                                    True)
        except Exception as e:
            Logger.error("Fullscreen::__update_background(): %s", e)

    def __update_datetime(self, show_seconds=False):
        """
            Update datetime in headerbar
            @param show_seconds as bool
        """
        now = datetime.now()
        if show_seconds:
            self._datetime.set_label(now.strftime("%a %d %b %X"))
        else:
            self._datetime.set_label(now.strftime("%a %d %b %X")[:-3])
        if self.__timeout_id is None:
            self.__timeout_id = GLib.timeout_add(60000, self.__update_datetime)
            return False
        return True

    def __on_artwork(self, surface, album_artwork):
        """
            Set background artwork
            @param surface as str
            @param album_artwork as bool
        """
        if surface is None and not album_artwork:
            self.__update_background(True)
        else:
            self.__background_artwork.set_from_surface(surface)

    def __on_key_release_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def __on_back_button_clicked(self, button):
        """
            Go back in container stack
            @param button as Gtk.Button
        """
        self.go_back()

    def __on_show_can_go_back(self, window, back):
        """
            Show back button
            @param window as Gtk.Window
            @param back as bool
        """
        if back:
            self.__back_button.show()
        else:
            self.__back_button.hide()

    def __on_can_go_back_changed(self, window, back):
        """
            Make button sensitive
            @param window as Gtk.Window
            @param back as bool
        """
        if back:
            self.__back_button.set_sensitive(True)
        else:
            self.__back_button.set_sensitive(False)

    def __on_size_allocate(self, widget, allocation):
        """
            Update background if needed
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if allocation.width <= 1 or\
                allocation.height <= 1 or\
                allocation.width == self.__allocation.width or\
                allocation.height == self.__allocation.height:
            return
        self.__allocation = allocation
        self.__update_background()
