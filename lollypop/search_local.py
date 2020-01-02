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

from gi.repository import GObject, GLib

from lollypop.define import App, Type
from lollypop.objects_album import Album
from lollypop.objects_track import Track


class LocalSearch(GObject.Object):
    """
        Local search
    """
    __gsignals__ = {
        "match-artist": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "match-album": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "match-track": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "search-finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init search
        """
        GObject.Object.__init__(self)
        self.__search_count = 0

    def get(self, search, storage_type, cancellable):
        """
            Get match for search
            @param current_search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        self.__search_count = 2
        items = self.__split_string(search)
        App().task_helper.run(self.__get_artists, items, storage_type,
                              cancellable)
        App().task_helper.run(self.__get_albums, items, storage_type,
                              cancellable)

#######################
# PRIVATE             #
#######################
    def __calculate_score(self, object, search_items):
        """
            Calculate string score for search items
            @param object as Track/Album
            @param search_item as str
        """
        score = 0
        for string in [object.name] + object.artists:
            string = string.lower()
            initial_score = 10 if string.startswith(search_items) else 0
            split_search = self.__split_string(search_items)
            split_string = self.__split_string(string)
            join = list(set(split_string) & set(split_search))
            score += initial_score + len(join)
        return score

    def __split_string(self, search_items):
        """
            Explose search items for all search possiblities
            @param search_items as [str]
            @return [str]
        """
        items = []
        for item in search_items.split():
            if len(item) > 3 and item != search_items:
                items.append(item)
        return [search_items] + sorted(items, key=len)

    def __search_tracks(self, search_items, storage_type, cancellable):
        """
            Get tracks for search items
            @param search_items as [str]
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
            @return [int]
        """
        track_ids = []
        for search_str in search_items:
            track_ids += App().tracks.search(search_str, storage_type)
            if cancellable.is_cancelled():
                break
        return list(set(track_ids))

    def __search_artists(self, search_items, storage_type, cancellable):
        """
            Get artists for search items
            @param search_items as [str]
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
            @return [int]
        """
        artist_ids = []
        for search_str in search_items:
            artist_ids = App().artists.search(search_str, storage_type)
            if cancellable.is_cancelled():
                break
        return artist_ids

    def __search_albums(self, search_items, storage_type, cancellable):
        """
            Get albums for search items
            @param search_items as [str]
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
            @return [int]
        """
        album_ids = []
        for search_str in search_items:
            album_ids = App().albums.search(search_str, storage_type)
            if cancellable.is_cancelled():
                break
        return album_ids

    def __get_artists(self, items, storage_type, cancellable):
        """
            Get artists for items
            @param items as [str]
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        artist_ids = self.__search_artists(items, storage_type, cancellable)
        if artist_ids:
            for artist_id in artist_ids:
                GLib.idle_add(self.emit, "match-artist", artist_id)
        else:
            GLib.idle_add(self.emit, "match-artist", Type.NONE)
        self.__search_count -= 1
        if self.__search_count == 0:
            GLib.idle_add(self.emit, "search-finished")

    def __get_albums(self, items, storage_type, cancellable):
        """
            Get albums for items
            @param items as [str]
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        album_ids = self.__search_albums(items, storage_type, cancellable)
        if album_ids:
            for album_id in album_ids:
                GLib.idle_add(self.emit, "match-album", album_id)
        else:
            GLib.idle_add(self.emit, "match-album", Type.NONE)
        self.__search_count -= 1
        if self.__search_count == 0:
            GLib.idle_add(self.emit, "search-finished")

    def __get(self, search_items, storage_type, cancellable):
        """
            Get track for name
            @param search_items as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
            @return items as [(int, Album, bool)]
        """
        split_items = self.__split_string(search_items)
        album_ids = self.__search_albums(split_items, storage_type,
                                         cancellable)
        track_ids = self.__search_tracks(split_items, storage_type,
                                         cancellable)
        albums = []
        all_album_ids = []
        album_tracks = {}

        # Merge albums for tracks
        for track_id in track_ids:
            if cancellable.is_cancelled():
                return []
            track = Track(track_id)
            # Get a new album
            album = track.album
            if album.id in album_tracks.keys():
                (album, tracks) = album_tracks[album.id]
                tracks.append(track)
                album_tracks[track.album.id] = (album, tracks)
            else:
                album_tracks[track.album.id] = (album, [track])

        # Create albums for album results
        for album_id in album_ids:
            if cancellable.is_cancelled():
                return []
            if album_id not in all_album_ids:
                all_album_ids.append(album_id)
                album = Album(album_id)
                score = self.__calculate_score(album, search_items)
                albums.append((score, album, False))
        # Create albums from track results
        for key in album_tracks.keys():
            if cancellable.is_cancelled():
                return []
            (album, tracks) = album_tracks[key]
            if album.id not in all_album_ids:
                album.set_tracks(tracks)
                score = self.__calculate_score(album, search_items)
                for track in album.tracks:
                    score += self.__calculate_score(track, search_items)
                all_album_ids.append(album.id)
                albums.append((score, album, True))
        albums.sort(key=lambda tup: tup[0], reverse=True)
        return [(album, in_tracks) for (score, album, in_tracks) in albums]
