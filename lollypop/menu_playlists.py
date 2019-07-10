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

from gi.repository import Gio

from gettext import gettext as _

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
        playlist_action = Gio.SimpleAction(name="playlist_action")
        App().add_action(playlist_action)
        playlist_action.connect("activate",
                                self.__add_to_playlists)
        self.append(_("Add to others"), "app.playlist_action")
        i = 0
        for playlist in App().playlists.get_last():
            action = Gio.SimpleAction(name="playlist%s" % i)
            App().add_action(action)
            if isinstance(self.__object, Album):
                exists = App().playlists.exists_album(playlist[0],
                                                      self.__object)
            else:
                exists = App().playlists.exists_track(playlist[0],
                                                      self.__object.uri)
            if exists:
                action.connect("activate",
                               self.__remove_from_playlist,
                               playlist[0])
                self.append(_("Remove from \"%s\"") % playlist[1],
                            "app.playlist%s" % i)
            else:
                action.connect("activate",
                               self.__add_to_playlist,
                               playlist[0])
                self.append(_("Add to \"%s\"") % playlist[1],
                            "app.playlist%s" % i)
            i += 1

    def __add_to_playlists(self, action, variant):
        """
            Add to playlists
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_playlist_manager(self.__object)

    def __add_to_playlist(self, action, variant, playlist_id):
        """
            Add to playlist
            @param Gio.SimpleAction
            @param GLib.Variant
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

    def __remove_from_playlist(self, action, variant, playlist_id):
        """
            Del from playlist
            @param Gio.SimpleAction
            @param GLib.Variant
            @param object id as int
            @param is album as bool
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
