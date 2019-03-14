# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import App
from lollypop.objects import Album, Track


class Search:
    """
        Local search
    """

    def __init__(self):
        """
            Init search
        """
        pass

    def get(self, current_search, ephemeral, cancellable, callback):
        """
            Get track for name (lowercase)
            @param current_search as str
            @param ephemeral as bool
            @param cancellable as Gio.Cancellable
            @param callback as callback
        """
        App().task_helper.run(self.__get, current_search, ephemeral,
                              cancellable, callback=callback)

#######################
# PRIVATE             #
#######################
    def __calculate_score(self, string, search_items):
        """
            Calculate string score for search items
            @param string as str
            @param search_item as str
        """
        string = string.lower()
        initial_score = 10 if string.startswith(search_items) else 0
        split_search = self.__split_string(search_items)
        split_string = self.__split_string(string)
        join = list(set(split_string) & set(split_search))
        return initial_score + len(join)

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

    def __search_artists(self, search_items, cancellable):
        """
            Get artists for search
            @param search_items as [str]
            @param cancellable as Gio.Cancellable
            @return (result [int], score as int)
        """
        artist_ids = []
        for search_str in search_items:
            artist_ids += App().artists.search(search_str)
            if cancellable.is_cancelled():
                break
        return list(set(artist_ids))

    def __search_tracks(self, search_items, ephemeral, cancellable):
        """
            Get tracks for search items
            @param search_items as [str]
            @param ephemeral as bool
            @param cancellable as Gio.Cancellable
            @return (result [int], score as int)
        """
        track_ids = []
        for search_str in search_items:
            track_ids += App().tracks.search(search_str, ephemeral)
            if cancellable.is_cancelled():
                break
        return list(set(track_ids))

    def __search_albums(self, search_items, ephemeral, cancellable):
        """
            Get albums for search items
            @param search_items as [str]
            @param ephemeral as bool
            @param cancellable as Gio.Cancellable
            @return (result [int], score as int)
        """
        album_ids = []
        for search_str in search_items:
            album_ids = App().albums.search(search_str, ephemeral)
            if cancellable.is_cancelled():
                break
        return list(set(album_ids))

    def __get(self, search_items, ephemeral, cancellable):
        """
            Get track for name
            @param search_items as str
            @param ephemeral as bool
            @param cancellable as Gio.Cancellable
            @return items as [(int, Album, bool)]
        """
        split_items = self.__split_string(search_items)
        album_ids = self.__search_albums(split_items, ephemeral, cancellable)
        track_ids = self.__search_tracks(split_items, ephemeral, cancellable)
        artist_ids = self.__search_artists(split_items, cancellable)
        albums = []
        all_album_ids = []

        # Merge albums for tracks
        album_tracks = {}
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
                score = self.__calculate_score(album.name, search_items)
                albums.append((score, album, False))
        # Get tracks/albums for artists
        for artist_id in artist_ids:
            if cancellable.is_cancelled():
                return []
            for album_id in App().albums.get_ids([artist_id], [],
                                                 False, ephemeral):
                if album_id not in all_album_ids:
                    album = Album(album_id)
                    score = self.__calculate_score(album.name, search_items)
                    for artist in album.artists:
                        score += self.__calculate_score(artist, search_items)
                    albums.append((score, album, False))
        # Create albums from track results
        for key in album_tracks.keys():
            if cancellable.is_cancelled():
                return []
            (album, tracks) = album_tracks[key]
            if album.id not in all_album_ids:
                album.set_tracks(tracks)
                score = self.__calculate_score(album.name, search_items)
                for track in album.tracks:
                    score += self.__calculate_score(track.name, search_items)
                all_album_ids.append(album.id)
                albums.append((score, album, True))
        albums.sort(key=lambda tup: tup[0], reverse=True)
        return [(album, in_tracks) for (score, album, in_tracks) in albums]
