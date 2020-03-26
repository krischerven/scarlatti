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


class CollectionItem:
    """
        A collection item with an track id and associated album/genres/artists
    """

    def __init__(self, track_id=None, album_id=None, new_album=False,
                 genre_ids=[], new_genre_ids=[], artist_ids=[],
                 new_artist_ids=[], album_artist_ids=[],
                 new_album_artist_ids=[]):
        """
            Init item
            @param track_id as int
            @param album_id as int
            @param new_album as bool
            @param genre_ids as [int]
            @param new_genre_ids as [int]
            @param artist_ids as [int]
            @param new_artist_ids as [int]
            @param album_artist_ids as [int]
            @param new_album_artist_ids as [int]
        """
        self.__track_id = track_id
        self.__album_id = album_id
        self.__new_album = new_album
        self.__genre_ids = genre_ids
        self.__new_genre_ids = new_genre_ids
        self.__artist_ids = artist_ids
        self.__new_artist_ids = new_artist_ids
        self.__album_artist_ids = album_artist_ids
        self.__new_album_artist_ids = new_album_artist_ids

    def set_track_id(self, track_id):
        """
            Set item track id
            @param track_id as int
        """
        self.__track_id = track_id

    def set_album_id(self, album_id, new_album=False):
        """
            Set item track id
            @param track_id as int
            @param new_album as bool
        """
        self.__album_id = album_id
        self.__new_album = new_album

    def set_genre_ids(self, genre_ids):
        """
            Set item genre_ids
            @param genre_ids as [int]
        """
        self.__genre_ids = genre_ids

    def set_new_genre_ids(self, genre_ids):
        """
            Set item new genre_ids
            @param genre_ids as [int]
        """
        self.__new_genre_ids = genre_ids

    def set_artist_ids(self, artist_ids):
        """
            Set item artist ids
            @param artist_ids as [int]
        """
        self.__artist_ids = artist_ids

    def set_new_artist_ids(self, artist_ids):
        """
            Set item new artist ids
            @param artist_ids as [int]
        """
        self.__new_artist_ids = artist_ids

    def set_album_artist_ids(self, artist_ids):
        """
            Set item album artist ids
            @param artist_ids as [int]
        """
        self.__album_artist_ids = artist_ids

    def set_new_album_artist_ids(self, artist_ids):
        """
            Set item new album artist ids
            @param artist_ids as [int]
        """
        self.__new_album_artist_ids = artist_ids

    @property
    def track_id(self):
        """
            Get track id
            @return int
        """
        return self.__track_id

    @property
    def album_id(self):
        """
            Get album id
            @return int
        """
        return self.__album_id

    @property
    def new_album(self):
        """
            True if album has been new for this item
            @return bool
        """
        return self.__new_album

    @property
    def genre_ids(self):
        """
            Get genre ids
            @return [int]
        """
        return self.__genre_ids

    @property
    def new_genre_ids(self):
        """
            Get new genre ids
            @return [int]
        """
        return self.__new_genre_ids

    @property
    def artist_ids(self):
        """
            Get artist ids
            @return [int]
        """
        return self.__artist_ids

    @property
    def new_artist_ids(self):
        """
            Get new artist ids
            @return [int]
        """
        return self.__new_artist_ids

    @property
    def album_artist_ids(self):
        """
            Get album_artist ids
            @return [int]
        """
        return self.__album_artist_ids

    @property
    def new_album_artist_ids(self):
        """
            Get new album artist ids
            @return [int]
        """
        return self.__new_album_artist_ids
