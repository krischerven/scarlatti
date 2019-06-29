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

from gi.repository import Gtk, GObject, GLib

from lollypop.helper_art import ArtBehaviour
from lollypop.controller_information import InformationController
from lollypop.controller_progress import ProgressController
from lollypop.controller_playback import PlaybackController
from lollypop.utils import on_realize
from lollypop.define import App, ArtSize, Type


class MiniPlayer(Gtk.Bin, InformationController,
                 ProgressController, PlaybackController):
    """
        Mini player shown in adaptive mode
    """
    __gsignals__ = {
        "revealed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self):
        """
            Init mini player
        """
        self.__size = 0
        self.__allocation_timeout_id = None
        self.__cover = None
        Gtk.Bin.__init__(self)
        InformationController.__init__(self, False,
                                       ArtBehaviour.BLUR_MAX |
                                       ArtBehaviour.DARKER)
        ProgressController.__init__(self)
        PlaybackController.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/MiniPlayer.ui")
        builder.connect_signals(self)

        self.get_style_context().add_class("black")
        self.__grid = builder.get_object("grid")
        self.__revealer = builder.get_object("revealer")
        self.__revealer_box = builder.get_object("revealer_box")
        self.__eventbox = builder.get_object("eventbox")
        self.__eventbox.connect("realize", on_realize)

        self._progress = builder.get_object("progress_scale")
        self._progress.set_sensitive(False)
        self._progress.set_hexpand(True)
        self._timelabel = builder.get_object("playback")
        self._total_time_label = builder.get_object("duration")

        self._artist_label = builder.get_object("artist_label")
        self._title_label = builder.get_object("title_label")

        self._prev_button = builder.get_object("previous_button")
        self._play_button = builder.get_object("play_button")
        self._next_button = builder.get_object("next_button")
        self.__back_button = builder.get_object("back_button")
        self._play_image = builder.get_object("play_image")
        self._pause_image = builder.get_object("pause_image")

        self.__grid = builder.get_object("grid")
        self._artwork = builder.get_object("cover")
        self.__signal_id1 = App().player.connect("current-changed",
                                                 self.__on_current_changed)
        self.__signal_id2 = App().player.connect("status-changed",
                                                 self.__on_status_changed)
        self.__signal_id3 = App().player.connect("duration-changed",
                                                 self.on_duration_changed)
        self.__on_current_changed(App().player)
        if App().player.current_track.id is not None:
            PlaybackController.on_status_changed(self, App().player)
            self.update_position()
            ProgressController.on_status_changed(self, App().player)
        self.add(builder.get_object("widget"))
        self.connect("size-allocate", self.__on_size_allocate)
        self.connect("destroy", self.__on_destroy)

    def do_get_preferred_width(self):
        """
            Force preferred width
        """
        (min, nat) = Gtk.Bin.do_get_preferred_width(self)
        # Allow resizing
        return (0, nat)

    def do_get_preferred_height(self):
        """
            Force preferred height
        """
        (min, nat) = self.__grid.get_preferred_height()
        return (min, min)

#######################
# PROTECTED           #
#######################
    def _on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is None:
            self.__grid.get_style_context().add_class("black")
            self._artwork.get_style_context().add_class("black")
        else:
            InformationController._on_album_artwork(self, surface)
            self.__grid.get_style_context().remove_class("black")
            self._artwork.get_style_context().remove_class("black")

    def _on_lyrics_button_clicked(self, button):
        """
            Show lyrics view
            @param button as Gtk.Button
        """
        self._on_button_release_event()
        App().window.container.show_lyrics()

    def _on_button_release_event(self, *ignore):
        """
            Set revealer on/off
            @param button as Gtk.Button
        """
        if self.__revealer.get_reveal_child():
            self.__revealer.set_reveal_child(False)
            self.emit("revealed", False)
            if self.__cover is not None:
                self.__cover.destroy()
                self.__cover = None
        else:
            if self.__cover is None:
                self.__cover = Gtk.Image.new()
                App().art_helper.set_frame(self.__cover,
                                           "small-cover-frame",
                                           ArtSize.MINIPLAYER,
                                           ArtSize.MINIPLAYER)
                self.__cover.set_property("halign", Gtk.Align.CENTER)
                self.__cover.set_property("valign", Gtk.Align.CENTER)
                self.__update_artwork()
                self.__cover.show()
                self.__revealer_box.pack_start(self.__cover,
                                               True, True, 0)
            self.__revealer.set_reveal_child(True)
            self.emit("revealed", True)

#######################
# PRIVATE             #
#######################
    def __update_artwork(self):
        """
            Update artwork based on current track
        """
        if App().player.current_track.id == Type.RADIOS:
            App().art_helper.set_radio_artwork(
                App().player.current_track.radio_name,
                ArtSize.MINIPLAYER,
                ArtSize.MINIPLAYER,
                self._artwork.get_scale_factor(),
                ArtBehaviour.CACHE | ArtBehaviour.CROP_SQUARE,
                self.__on_artwork)
        else:
            App().art_helper.set_album_artwork(
                App().player.current_track.album,
                ArtSize.MINIPLAYER,
                ArtSize.MINIPLAYER,
                self._artwork.get_scale_factor(),
                ArtBehaviour.CACHE | ArtBehaviour.CROP_SQUARE,
                self.__on_artwork)

    def __handle_size_allocate(self, allocation):
        """
            Change box max/min children
            @param allocation as Gtk.Allocation
        """
        self.__allocation_timeout_id = None
        # We use parent height because we may be collapsed
        parent = self.get_parent()
        if parent is None:
            height = allocation.height
        else:
            height = parent.get_allocated_height()
        new_size = max(allocation.width, height)
        if new_size == 1 or self.__size == new_size:
            return
        self.__size = new_size
        self._previous_artwork_id = None
        InformationController.on_current_changed(self, new_size, None)

    def __on_destroy(self, widget):
        """
            Handle widget cleanup
            @param widget as Gtk.Widget
        """
        ProgressController.on_destroy(self)
        PlaybackController.on_destroy(self)
        App().player.disconnect(self.__signal_id1)
        App().player.disconnect(self.__signal_id2)
        App().player.disconnect(self.__signal_id3)

    def __on_current_changed(self, player):
        """
            Update controllers
            @param player as Player
        """
        if App().player.current_track.id is not None:
            self.show()
        InformationController.on_current_changed(self, self.__size, None)
        ProgressController.on_current_changed(self, player)
        PlaybackController.on_current_changed(self, player)
        if self.__cover is not None:
            self.__update_artwork()

    def __on_status_changed(self, player):
        """
            Update controllers
            @param player as Player
        """
        ProgressController.on_status_changed(self, player)
        PlaybackController.on_status_changed(self, player)

    def __on_size_allocate(self, widget, allocation):
        """
            Delayed handling
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__allocation_timeout_id is not None:
            GLib.source_remove(self.__allocation_timeout_id)
        self.__allocation_timeout_id = GLib.idle_add(
            self.__handle_size_allocate, allocation)

    def __on_artwork(self, surface):
        """
            Set artwork
            @param surface as str
        """
        if surface is None:
            self.__cover.get_style_context().add_class("white")
            if App().player.current_track.id == Type.RADIOS:
                icon_name = "audio-input-microphone-symbolic"
            else:
                icon_name = "folder-music-symbolic"
            self.__cover.set_from_icon_name(icon_name,
                                            Gtk.IconSize.DIALOG)
        else:
            self.__cover.get_style_context().remove_class("white")
            self.__cover.set_from_surface(surface)
