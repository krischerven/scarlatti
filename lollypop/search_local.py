# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GObject, GLib

from collections import Counter

from lollypop.define import App
from lollypop.utils import noaccents, regexpr_and_valid


class LocalSearch(GObject.Object):
    """
        Local search
    """
    __gsignals__ = {
        "match-artist": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-album": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-track": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init search
        """
        GObject.Object.__init__(self)

    def get(self, search, storage_type, cancellable):
        """
            Get match for search
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        search = noaccents(search)
        self.__get_artists(search, storage_type, cancellable)
        self.__get_albums(search, storage_type, cancellable)
        self.__get_tracks(search, storage_type, cancellable)
        GLib.idle_add(self.emit, "finished")

#######################
# PRIVATE             #
#######################
    def __split_string(self, string):
        """
            Split string for search
            @param string as str
            @return str
        """
        split = []
        nextWord = ""
        for word in string.split():
            if word.startswith("\""):
                nextWord = word[1:]
                if word.endswith("\""):
                    word = nextWord[:-1]
                    nextWord = ""
                    split.append(word)
            elif word.endswith("\"") and nextWord != "":
                word = nextWord+" "+word[:-1]
                nextWord = ""
                split.append(word)
            else:
                # Unfinished word or intentional quote
                if nextWord != "":
                    split.append("\""+nextWord)
                    nextWord = ""
                split.append(word)
        # Unfinished word or intentional quote
        if nextWord != "":
            split.append("\""+nextWord)
        return split

    def __search_tracks(self, search, storage_type, cancellable):
        """
            Get tracks for search items
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
            @return [int]
        """

        tracks = []
        track_ids = []
        split = self.__split_string(search)

        if search.startswith("\"") and search.endswith("\""):
            search = search[1:-1]

        for search_str in [search] + split:
            tracks += App().tracks.search_performed(search_str, storage_type)
            tracks += App().tracks.search(search_str, storage_type)
            if cancellable.is_cancelled():
                break
        for (track_id, track_name) in tracks:
            valid = True
            track_name = noaccents(track_name)
            if not track_name.startswith(search):
                for word in split:
                    if not regexpr_and_valid(word, track_name) and word not in track_name:
                        valid = False
                        break
            # Track starts with all the same words, adding to result
            else:
                track_ids.append(track_id)
            # All words are valid for this track (or valid regexpr), adding to result
            if valid:
                track_ids.append(track_id)
            # Detected an artist match, adding to result
            for artist in App().tracks.get_artists(track_id):
                valid = True
                for word in [w for w in split if w != noaccents(artist)]:
                    if not regexpr_and_valid(word, track_name) and word not in track_name:
                        valid = False
                        break
                if valid:
                    track_ids.append(track_id)
        return track_ids

    def __search_artists(self, search, storage_type, cancellable):
        """
            Get artists for search items
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
            @return [int]
        """
        artists = []
        artist_ids = []
        split = self.__split_string(search)
        for search_str in [search] + split:
            artists += App().artists.search(search_str, storage_type)
            if cancellable.is_cancelled():
                break
        for (artist_id, artist_name) in artists:
            valid = True
            artist_name = noaccents(artist_name)
            if not artist_name.startswith(search):
                for word in split:
                    if not regexpr_and_valid(word, artist_name) and word not in artist_name:
                        valid = False
                        break
            # Artist starts with all the same words, adding to result
            else:
                artist_ids.append(artist_id)
            # All words are valid for this artist (or valid regexpr), adding to result
            if valid:
                artist_ids.append(artist_id)
        return artist_ids

    def __search_albums(self, search, storage_type, cancellable):
        """
            Get albums for search items
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
            @return [int]
        """
        albums = []
        album_ids = []
        split = self.__split_string(search)
        for search_str in [search] + split:
            albums += App().albums.search(search_str, storage_type)
            if cancellable.is_cancelled():
                break
        for (album_id, album_name) in albums:
            valid = True
            album_name = noaccents(album_name)
            if not album_name.startswith(search):
                for word in split:
                    if not regexpr_and_valid(word, album_name) and word not in album_name:
                        valid = False
                        break
            # Album starts with all the same words, adding to result
            else:
                album_ids.append(album_id)
            # All words are valid for this album (or valid regexpr), adding to result
            if valid:
                album_ids.append(album_id)
        return album_ids

    def __get_artists(self, search, storage_type, cancellable):
        """
            Get artists for search
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        artist_ids = self.__search_artists(search, storage_type, cancellable)
        counter = Counter(artist_ids)
        artist_ids = sorted(artist_ids,
                            key=lambda x: (counter[x], x),
                            reverse=True)
        artist_ids = list(dict.fromkeys(artist_ids))
        for artist_id in artist_ids:
            GLib.idle_add(self.emit, "match-artist", artist_id, storage_type)

    def __get_albums(self, search, storage_type, cancellable):
        """
            Get albums for search
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        album_ids = self.__search_albums(search, storage_type, cancellable)
        counter = Counter(album_ids)
        album_ids = sorted(album_ids,
                           key=lambda x: (counter[x], x),
                           reverse=True)
        album_ids = list(dict.fromkeys(album_ids))
        for album_id in album_ids:
            GLib.idle_add(self.emit, "match-album", album_id, storage_type)

    def __get_tracks(self, search, storage_type, cancellable):
        """
            Get tracks for search
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        track_ids = self.__search_tracks(search, storage_type, cancellable)
        counter = Counter(track_ids)
        track_ids = sorted(track_ids,
                           key=lambda x: (counter[x], x),
                           reverse=True)
        track_ids = list(dict.fromkeys(track_ids))
        for track_id in track_ids:
            GLib.idle_add(self.emit, "match-track", track_id, storage_type)
