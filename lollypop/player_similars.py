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

from random import shuffle

from lollypop.objects import Album
from lollypop.logger import Logger
from lollypop.define import App, Repeat
from lollypop.utils import get_network_available


class SimilarsPlayer:
    """
        Manage playback when going to end
    """

    def __init__(self):
        """
            Init player
        """
        self.__cancellable = Gio.Cancellable()
        self.connect("next-changed", self.__on_next_changed)

#######################
# PRIVATE             #
#######################
    def __add_a_new_album(self, similar_artist_ids):
        """
            Add a new album to playback
            @param similar_artist_ids as [int]
        """
        # Get an album
        album_ids = App().albums.get_ids(similar_artist_ids, [])
        shuffle(album_ids)
        while album_ids:
            album_id = album_ids.pop(0)
            if album_id not in self.album_ids:
                self.add_album(Album(album_id))
                break

    def __get_artist_ids(self, artists):
        """
            Get a valid artist id from list
            @param artists as [str]
            @return artist_id as int
        """
        similar_artist_ids = []
        for artist in artists:
            similar_artist_id = App().artists.get_id(artist)
            if similar_artist_id is not None:
                if App().artists.get_albums([similar_artist_id]):
                    similar_artist_ids.append(similar_artist_id)
        return similar_artist_ids

    def __on_next_changed(self, player):
        """
            Add a new album if playback finished and wanted by user
        """
        # Check if we need to add a new album
        if App().settings.get_enum("repeat") == Repeat.AUTO and\
                player.next_track.id is None and\
                player.current_track.id is not None and\
                player.current_track.id >= 0 and\
                Gio.NetworkMonitor.get_default().get_network_available() and\
                player.current_track.artist_ids:
            artist_id = player.current_track.artist_ids[0]
            artist_name = App().artists.get_name(artist_id)
            if App().lastfm is not None and get_network_available("LASTFM"):
                App().task_helper.run(
                              App().lastfm.get_similar_artists,
                              artist_name, self.__cancellable,
                              callback=(self.__on_lastfm_similar_artists,))
            elif get_network_available("SPOTIFY"):
                App().spotify.get_artist_id(artist_name,
                                            self.__on_get_spotify_artist_id)

    def __on_get_spotify_artist_id(self, artist_id):
        """
            Get similars
            @param artist_id as str
        """
        if artist_id is None:
            return
        App().task_helper.run(App().spotify.get_similar_artists,
                              artist_id, self.__cancellable,
                              callback=(self.__on_spotify_similar_artists,))

    def __on_lastfm_similar_artists(self, artists):
        """
            Add one album or run a Spotify search if none
            @param artists as [str]
        """
        similar_artist_ids = self.__get_artist_ids(artists)
        if not similar_artist_ids:
            if self.current_track.artist_ids:
                artist_id = self.current_track.artist_ids[0]
                artist_name = App().artists.get_name(artist_id)
                App().spotify.get_artist_id(artist_name,
                                            self.__on_get_spotify_artist_id)
        else:
            Logger.info("Found a similar artist via Last.fm")
            if self.albums:
                self.__add_a_new_album(similar_artist_ids)

    def __on_spotify_similar_artists(self, artists):
        """
            Add one album
            @param artists as [str]
        """
        similar_artist_ids = self.__get_artist_ids(artists)
        if similar_artist_ids:
            Logger.info("Found similar artists via Spotify:")
            if self.albums:
                self.__add_a_new_album(similar_artist_ids)
