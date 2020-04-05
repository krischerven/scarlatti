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

from gi.repository import Gio

from random import shuffle

from lollypop.objects_album import Album
from lollypop.objects_track import Track
from lollypop.logger import Logger
from lollypop.define import App, Repeat, StorageType
from lollypop.utils import sql_escape, get_network_available
from lollypop.utils import get_default_storage_type
from lollypop.utils_album import tracks_to_albums


class AutoSimilarPlayer:
    """
        Manage playback when going to end
    """

    def __init__(self):
        """
            Init player
        """
        self.__next_cancellable = Gio.Cancellable()
        self.__radio_cancellable = Gio.Cancellable()
        self.connect("next-changed", self.__on_next_changed)

    def next_album(self):
        """
            Get next album to add
            @return Album
        """
        genre_ids = App().artists.get_genre_ids(self.current_track.artist_ids,
                                                StorageType.COLLECTION)
        track_ids = App().tracks.get_randoms(genre_ids,
                                             StorageType.COLLECTION,
                                             1)
        if track_ids:
            return Track(track_ids[0]).album
        return None

    def play_radio(self, artist_ids):
        """
            Play a radio based on current artist
            @param artist_ids as [int]
        """
        self.__radio_cancellable.cancel()
        self.__radio_cancellable = Gio.Cancellable()

        def on_match_track(similars, track_id, storage_type):
            track = Track(track_id)
            if self.albums:
                self.add_album(track.album)
            else:
                self.play_album(track.album)

        def on_finished(similars):
            self.__radio_cancellable.cancel()

        if get_network_available("SPOTIFY") and\
                get_network_available("YOUTUBE"):
            from lollypop.similars_spotify import SpotifySimilars
            similars = SpotifySimilars()
            similars.connect("match-track", on_match_track)
            similars.connect("finished", on_finished)
            self.clear_albums()
            App().task_helper.run(similars.load_similars,
                                  artist_ids,
                                  StorageType.EPHEMERAL,
                                  self.__radio_cancellable)
        else:
            genre_ids = App().artists.get_genre_ids(artist_ids,
                                                    StorageType.COLLECTION)
            track_ids = App().tracks.get_randoms(genre_ids,
                                                 StorageType.COLLECTION,
                                                 100)
            albums = tracks_to_albums(
                [Track(track_id) for track_id in track_ids])
            self.play_albums(albums)

#######################
# PRIVATE             #
#######################
    def __get_album_from_artists(self,  similar_artist_ids):
        """
            Add a new album to playback
            @param similar_artist_ids as [int]
            @return Album
        """
        # Get an album
        storage_type = get_default_storage_type()
        album_ids = App().albums.get_ids([], similar_artist_ids, storage_type)
        shuffle(album_ids)
        while album_ids:
            album_id = album_ids.pop(0)
            if album_id not in self.album_ids:
                return Album(album_id)
        return None

    def __get_artist_ids(self, artists):
        """
            Get valid artist ids from list
            @param artists as []
            @return [int]
        """
        similar_artist_ids = []
        for (artist, cover_uri) in artists:
            similar_artist_id = App().artists.get_id_for_escaped_string(
                sql_escape(artist.lower()))
            if similar_artist_id is not None:
                if App().artists.has_albums(similar_artist_id):
                    similar_artist_ids.append(similar_artist_id)
        return similar_artist_ids

    def __on_get_local_similar_artists(self, artists):
        """
            Add one album from artists to player
            @param artists as []
        """
        if self.__next_cancellable.is_cancelled():
            return
        similar_artist_ids = self.__get_artist_ids(artists)
        album = None
        if similar_artist_ids:
            album = self.__get_album_from_artists(similar_artist_ids)
        if album is not None:
            Logger.info("Found a similar album")
            self.add_album(album)

    def __on_get_similar_artists(self, artists):
        """
            Add one album from artists to player
            @param artists as []
        """
        if self.__next_cancellable.is_cancelled():
            return
        similar_artist_ids = self.__get_artist_ids(artists)
        album = None
        if similar_artist_ids:
            album = self.__get_album_from_artists(similar_artist_ids)
        if album is None:
            from lollypop.similars_local import LocalSimilars
            similars = LocalSimilars()
            App().task_helper.run(
                similars.get_similar_artists,
                App().player.current_track.artist_ids,
                self.__next_cancellable,
                callback=(self.__on_get_local_similar_artists,))
        else:
            Logger.info("Found a similar album")
            self.add_album(album)

    def __on_next_changed(self, player):
        """
            Add a new album if playback finished and wanted by user
        """
        self.__next_cancellable.cancel()
        # Do not load an album if a radio is loading
        if not self.__radio_cancellable.is_cancelled():
            return
        self.__next_cancellable = Gio.Cancellable()
        # Check if we need to add a new album
        if App().settings.get_enum("repeat") == Repeat.AUTO_SIMILAR and\
                player.next_track.id is None and\
                player.current_track.id is not None and\
                player.current_track.id >= 0 and\
                player.current_track.artist_ids:
            from lollypop.similars import Similars
            similars = Similars()
            App().task_helper.run(
                similars.get_similar_artists,
                player.current_track.artist_ids,
                self.__next_cancellable,
                callback=(self.__on_get_similar_artists,))
