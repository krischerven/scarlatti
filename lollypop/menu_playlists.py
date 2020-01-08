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

from gi.repository import Gio, GLib

from gettext import gettext as _
from hashlib import sha256

from lollypop.define import App
from lollypop.objects_track import Track
from lollypop.objects_album import Album


class PlaylistsMenu(Gio.Menu):
    """
        Contextual menu for playlists
    """

    def __init__(self, object):
        """
            Init playlist menu
            @param object as Album/Track
        """
        Gio.Menu.__init__(self)
        self.__object = object
        self.__set_playlist_actions()

#######################
# PRIVATE             #
#######################
    def __set_playlist_actions(self):
        """
            Set playlist actions
        """
        add_action = Gio.SimpleAction(name="add_to_new")
        App().add_action(add_action)
        add_action.connect("activate", self.__on_add_action_activate)
        self.append(_("New playlist"), "app.add_to_new")
        i = 1
        for (playlist_id, name) in App().playlists.get():
            if isinstance(self.__object, Album):
                exists = App().playlists.exists_album(playlist_id,
                                                      self.__object)
            else:
                exists = App().playlists.exists_track(playlist_id,
                                                      self.__object.uri)
            encoded = sha256(name.encode("utf-8")).hexdigest()
            playlist_action = Gio.SimpleAction.new_stateful(
                                          encoded,
                                          None,
                                          GLib.Variant.new_boolean(exists))
            playlist_action.connect("change-state",
                                    self.__on_playlist_action_change_state,
                                    playlist_id)
            App().add_action(playlist_action)
            self.append(name, "app.%s" % encoded)
            i += 1

    def __add_to_playlist(self, playlist_id):
        """
            Add to playlist
            @param playlist_id as int
        """
        def add(playlist_id):
            tracks = []
            if isinstance(self.__object, Album):
                for track_id in self.__object.track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self.__object.id)]
            App().playlists.add_tracks(playlist_id, tracks, True)
        App().task_helper.run(add, playlist_id)

    def __remove_from_playlist(self, playlist_id):
        """
            Del from playlist
            @param playlist_id as int
        """
        def remove(playlist_id):
            tracks = []
            if isinstance(self.__object, Album):
                for track_id in self.__object.track_ids:
                    tracks.append(Track(track_id))
            else:
                tracks = [Track(self.__object.id)]
            App().playlists.remove_tracks(playlist_id, tracks, True)
        App().task_helper.run(remove, playlist_id)

    def __add_to_loved(self, action, variant):
        """
            Add to loved
            @param Gio.SimpleAction
            @param GLib.Variant
            @param playlist name as str
        """
        self.__object.set_loved(True)

    def __del_from_loved(self, action, variant):
        """
            Remove from loved
            @param Gio.SimpleAction
            @param GLib.Variant
            @param playlist name as str
        """
        self.__object.set_loved(False)

    def __on_playlist_action_change_state(self, action, variant, playlist_id):
        """
            Add/Remove object from playlist
            @param Gio.SimpleAction
            @param GLib.Variant
            @param playlist_id as int
        """
        action.set_state(variant)
        if variant:
            self.__add_to_playlist(playlist_id)
        else:
            self.__remove_from_playlist(playlist_id)

    def __on_add_action_activate(self, action, variant):
        """
            Add a new playlist and add object to playlist
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        playlist_id = App().playlists.add(App().playlists.get_new_name())
        self.__add_to_playlist(playlist_id)
