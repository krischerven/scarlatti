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

from gi.repository import GObject, Gtk
from lollypop.define import App, Type


class TracksWidget(Gtk.ListBox):
    """
        A list of tracks
    """

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST,
                      None, (GObject.TYPE_PYOBJECT,))
    }

    def __init__(self):
        """
            Init track widget
        """
        Gtk.ListBox.__init__(self)
        self.connect("destroy", self.__on_destroy)
        self.__queue_signal_id = App().player.connect("queue-changed",
                                                      self.__on_queue_changed)
        self.__loved_signal_id1 = App().playlists.connect(
            "playlist-track-added",
            self.__on_loved_playlist_changed)
        self.__loved_signal_id2 = App().playlists.connect(
            "playlist-track-removed",
            self.__on_loved_playlist_changed)
        self.connect("row-activated", self.__on_activate)
        self.get_style_context().add_class("trackswidget")
        self.set_property("hexpand", True)
        self.set_property("selection-mode", Gtk.SelectionMode.NONE)

    def update_playing(self, track_id):
        """
            Update playing track
            @param track_id as int
        """
        for row in self.get_children():
            row.set_indicator()

    def update_duration(self, track_id):
        """
            Update duration for track id
            @param track_id as int
        """
        for row in self.get_children():
            if row.track.id == track_id:
                row.update_duration()

#######################
# PRIVATE             #
#######################
    def __on_queue_changed(self, unused):
        """
            Update all position labels
        """
        for row in self.get_children():
            row.update_number_label()

    def __on_loved_playlist_changed(self, widget, playlist_id, uri):
        """
            Updates the loved icon
            @param playlist as Playlist
            @param playlist_id as int
            @param uri as str
        """
        if playlist_id != Type.LOVED:
            return
        track_id = App().tracks.get_id_by_uri(uri)
        for row in self.get_children():
            if track_id == row.track.id:
                row.set_indicator()

    def __on_destroy(self, widget):
        """
            Remove signals
            @param widget as Gtk.Widget
        """
        if self.__queue_signal_id is not None:
            App().player.disconnect(self.__queue_signal_id)
            self.__queue_signal_id = None
        if self.__loved_signal_id1 is not None:
            App().playlists.disconnect(self.__loved_signal_id1)
            self.__loved_signal_id1 = None
        if self.__loved_signal_id2 is not None:
            App().playlists.disconnect(self.__loved_signal_id2)
            self.__loved_signal_id2 = None

    def __on_activate(self, widget, row):
        """
            Play activated item
            @param widget as TracksWidget
            @param row as TrackRow
        """
        self.emit("activated", row.track)
