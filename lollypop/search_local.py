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

from collections import Counter

from lollypop.define import App


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
        self.__search_count = 3
        items = self.__split_string(search)
        App().task_helper.run(self.__get_artists, items, storage_type,
                              cancellable)
        App().task_helper.run(self.__get_albums, items, storage_type,
                              cancellable)
        App().task_helper.run(self.__get_tracks, items, storage_type,
                              cancellable)

#######################
# PRIVATE             #
#######################
    def __split_string(self, search_items):
        """
            Explose search items for all search possiblities
            @param search_items as str
            @return [str]
        """
        split = search_items.split()
        i = len(split)
        if i > 1:
            items = [" %s" % split[i - 1]]
            i -= 1
        else:
            items = []
        while i != 0:
            if i > 1:
                items.append(" %s " % split[i - 1])
            else:
                items.append("%s " % split[0])
            i -= 1
        return [search_items] + items

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
        return track_ids

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
            artist_ids += App().artists.search(search_str, storage_type)
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
            album_ids += App().albums.search(search_str, storage_type)
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
        counter = Counter(artist_ids)
        artist_ids = sorted(artist_ids,
                            key=lambda x: (counter[x], x),
                            reverse=True)
        artist_ids = list(dict.fromkeys(artist_ids))
        for artist_id in artist_ids:
            GLib.idle_add(self.emit, "match-artist", artist_id)
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
        counter = Counter(album_ids)
        album_ids = sorted(album_ids,
                           key=lambda x: (counter[x], x),
                           reverse=True)
        album_ids = list(dict.fromkeys(album_ids))
        for album_id in album_ids:
            GLib.idle_add(self.emit, "match-album", album_id)
        self.__search_count -= 1
        if self.__search_count == 0:
            GLib.idle_add(self.emit, "search-finished")

    def __get_tracks(self, items, storage_type, cancellable):
        """
            Get tracks for items
            @param items as [str]
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        track_ids = self.__search_tracks(items, storage_type, cancellable)
        counter = Counter(track_ids)
        track_ids = sorted(track_ids,
                           key=lambda x: (counter[x], x),
                           reverse=True)
        track_ids = list(dict.fromkeys(track_ids))[0:10]
        for track_id in track_ids:
            GLib.idle_add(self.emit, "match-track", track_id)
        self.__search_count -= 1
        if self.__search_count == 0:
            GLib.idle_add(self.emit, "search-finished")
