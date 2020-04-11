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
        self.track_id = track_id
        self.album_id = album_id
        self.new_album = new_album
        self.genre_ids = genre_ids
        self.new_genre_ids = new_genre_ids
        self.artist_ids = artist_ids
        self.new_artist_ids = new_artist_ids
        self.album_artist_ids = album_artist_ids
        self.new_album_artist_ids = new_album_artist_ids
