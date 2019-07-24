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

from gettext import gettext as _
import itertools

from lollypop.sqlcursor import SqlCursor
from lollypop.define import App, Type, StorageType
from lollypop.utils import get_default_storage_type
from lollypop.utils import format_artist_name, noaccents, remove_static


class ArtistsDatabase:
    """
        Artists database helper
    """

    def __init__(self):
        """
            Init artists database object
        """
        pass

    def add(self, name, sortname, mb_artist_id):
        """
            Add a new artist to database
            @param name as string
            @param sortname as string
            @param mb_artist_id as str
            @return inserted rowid as int
            @warning: commit needed
        """
        if sortname == "":
            sortname = format_artist_name(name)
        with SqlCursor(App().db, True) as sql:
            result = sql.execute("INSERT INTO artists (name, sortname,\
                                  mb_artist_id)\
                                  VALUES (?, ?, ?)",
                                 (name, sortname, mb_artist_id))
            return result.lastrowid

    def set_sortname(self, artist_id, sort_name):
        """
            Set sort name
            @param artist_id as int
            @param sort_name a str
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE artists\
                         SET sortname=?\
                         WHERE rowid=?",
                        (sort_name, artist_id))

    def get_sortname(self, artist_id):
        """
            Return sortname
            @param artist_id as int
            @return sortname as string
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT sortname from artists\
                                  WHERE rowid=?", (artist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return self.get_name(artist_id)

    def get_id(self, name, mb_artist_id=None):
        """
            Get artist id
            @param name as string
            @param mb_artist_id as str
            @return Artist id as int
        """
        # Special case, id name is fully uppercase, do not use NOCASE
        # We want to have a different artist
        with SqlCursor(App().db) as sql:
            query = "SELECT rowid from artists\
                     WHERE name=?"
            params = [name]
            if mb_artist_id:
                query += " AND (mb_artist_id=? OR mb_artist_id IS NULL)"
                params.append(mb_artist_id)
            if not name.isupper():
                query += " COLLATE NOCASE"
            result = sql.execute(query, params)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_name(self, artist_id):
        """
            Get artist name
            @param artist_id as int
            @return str
        """
        with SqlCursor(App().db) as sql:
            if artist_id == Type.COMPILATIONS:
                return _("Many artists")

            result = sql.execute("SELECT name from artists WHERE rowid=?",
                                 (artist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def set_mb_artist_id(self, artist_id, mb_artist_id):
        """
            Set MusicBrainz artist id
            @param artist_id as int
            @param mb_artist_id as str
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE artists\
                         SET mb_artist_id=?\
                         WHERE rowid=?",
                        (mb_artist_id, artist_id))

    def get_mb_artist_id(self, artist_id):
        """
            Get MusicBrainz artist id for artist id
            @param artist_id as int
            @return MusicBrainz artist id as str
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT mb_artist_id FROM albums\
                                  WHERE rowid=?", (artist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return -1

    def get_albums(self, artist_ids):
        """
            Get all availables albums for artists
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            request = "SELECT DISTINCT albums.rowid\
                       FROM album_artists, albums\
                       WHERE albums.rowid=album_artists.album_id AND(1=0 "
            for artist_id in artist_ids:
                request += "OR album_artists.artist_id=%s " % artist_id
            request += ") ORDER BY year"
            result = sql.execute(request)
            return list(itertools.chain(*result))

    def get_compilations(self, artist_ids):
        """
            Get all availables compilations for artist
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            request = "SELECT DISTINCT albums.rowid FROM albums,\
                       tracks, track_artists, album_artists\
                       WHERE track_artists.track_id=tracks.rowid\
                       AND album_artists.artists_id=%s\
                       AND album_artists.album_id=albums.rowid\
                       AND albums.rowid=tracks.album_id AND (1=0 " %\
                Type.COMPILATIONS
            for artist_id in artist_ids:
                request += "OR track_artists.artist_id=%s " % artist_id
            request += ") ORDER BY albums.year"
            result = sql.execute(request)
            return list(itertools.chain(*result))

    def get(self, genre_ids=[]):
        """
            Get all available album artists
            @param genre_ids as [int]
            @return [int, str, str]
        """
        genre_ids = remove_static(genre_ids)
        if App().settings.get_value("show-artist-sort"):
            select = "artists.rowid, artists.sortname, artists.sortname"
        else:
            select = "artists.rowid, artists.name, artists.sortname"
        with SqlCursor(App().db) as sql:
            result = []
            storage_type = get_default_storage_type()
            if not genre_ids or genre_ids[0] == Type.ALL:
                # Only artist that really have an album
                result = sql.execute(
                    "SELECT DISTINCT %s FROM artists, albums, album_artists\
                                  WHERE album_artists.artist_id=artists.rowid\
                                  AND album_artists.album_id=albums.rowid\
                                  AND albums.storage_type & ?\
                                  ORDER BY artists.sortname\
                                  COLLATE NOCASE COLLATE LOCALIZED" % select,
                    (storage_type,))
            else:
                filters = (storage_type,)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT %s\
                           FROM artists, albums, album_genres, album_artists\
                           WHERE artists.rowid=album_artists.artist_id\
                           AND albums.rowid=album_artists.album_id\
                           AND albums.storage_type & ?\
                           AND album_genres.album_id=albums.rowid AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0) ORDER BY artists.sortname\
                            COLLATE NOCASE COLLATE LOCALIZED"
                result = sql.execute(request % select, filters)
            return [(row[0], row[1], row[2]) for row in result]

    def get_all(self, genre_ids=[]):
        """
            Get all available artists
            @param genre_ids as [int]
            @return [int, str, str]
        """
        if App().settings.get_value("show-artist-sort"):
            select = "artists.rowid, artists.sortname, artists.sortname"
        else:
            select = "artists.rowid, artists.name, artists.sortname"
        with SqlCursor(App().db) as sql:
            result = []
            storage_type = get_default_storage_type()
            if not genre_ids or genre_ids[0] == Type.ALL:
                # Only artist that really have an album
                result = sql.execute(
                    "SELECT DISTINCT %s FROM artists, track_artists, tracks\
                                  WHERE artists.rowid=track_artists.artist_id\
                                  AND tracks.rowid=track_artists.track_id\
                                  AND tracks.storage_type & ?\
                                  ORDER BY artists.sortname\
                                  COLLATE NOCASE COLLATE LOCALIZED" % select,
                    (storage_type,))
            else:
                filters = (storage_type,)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT %s\
                           FROM artists, tracks, track_genres, track_artists\
                           WHERE artists.rowid=track_artists.artist_id\
                           AND tracks.rowid=track_artists.track_id\
                           AND tracks.storage_type & ?\
                           AND track_genres.track_id=tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0) ORDER BY artists.sortname\
                            COLLATE NOCASE COLLATE LOCALIZED"
                result = sql.execute(request % select, filters)
            return [(row[0], row[1], row[2]) for row in result]

    def get_randoms(self, limit):
        """
            Return random artists
            @param limit as int
            @return [int, str, str]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            request = "SELECT DISTINCT artists.rowid,\
                                       artists.name,\
                                       artists.sortname\
                                  FROM artists, albums, album_artists\
                                  WHERE album_artists.artist_id=artists.rowid\
                                  AND album_artists.album_id=albums.rowid\
                                  AND albums.storage_type & ?\
                                  AND albums.loved != -1\
                                  ORDER BY random() LIMIT ?\
                                  COLLATE NOCASE COLLATE LOCALIZED"
            result = sql.execute(request, (storage_type, limit))
            return [(row[0], row[1], row[2]) for row in result]

    def get_ids(self, genre_ids=[]):
        """
            Get all available album artists
            @param genre_ids as [int]
            @return artist ids as [int]
        """
        with SqlCursor(App().db) as sql:
            result = []
            storage_type = get_default_storage_type()
            if not genre_ids or genre_ids[0] == Type.ALL:
                # Only artist that really have an album
                result = sql.execute(
                    "SELECT DISTINCT artists.rowid\
                                  FROM artists, albums, album_artists\
                                  WHERE album_artists.artist_id=artists.rowid\
                                  AND album_artists.album_id=albums.rowid\
                                  AND albums.storage_type & ?\
                                  ORDER BY artists.sortname\
                                  COLLATE NOCASE COLLATE LOCALIZED",
                    (storage_type,))
            else:
                filters = (storage_type,)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT artists.rowid\
                           FROM artists, albums, album_genres, album_artists\
                           WHERE artists.rowid=album_artists.artist_id\
                           AND albums.storage_type & ?\
                           AND albums.rowid=album_artists.album_id\
                           AND album_genres.album_id=albums.rowid AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0) ORDER BY artists.sortname\
                            COLLATE NOCASE COLLATE LOCALIZED"
                result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def exists(self, artist_id):
        """
            Return True if artist exist
            @param artist_id as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT COUNT(1) FROM artists WHERE rowid=?",
                                 (artist_id,))
            v = result.fetchone()
            if v is not None:
                return bool(v[0])
            return False

    def search(self, searched):
        """
            Search for artists looking like string
            @param searched as str
            @return [int]
        """
        no_accents = noaccents(searched)
        with SqlCursor(App().db) as sql:
            items = []
            for filter in [(no_accents + "%",),
                           ("%" + no_accents,),
                           ("%" + no_accents + "%",)]:
                request = "SELECT artists.rowid\
                           FROM artists, albums, album_artists\
                           WHERE noaccents(artists.name) LIKE ? LIMIT 25"
                result = sql.execute(request, filter)
                items += list(itertools.chain(*result))
            return items

    def count(self):
        """
            Count artists
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT COUNT(DISTINCT artists.rowid)\
                                  FROM artists, album_artists, albums\
                                  WHERE album_artists.album_id=albums.rowid\
                                  AND artists.rowid=album_artists.artist_id\
                                  AND albums.storage_type & ?",
                                 StorageType.COLLECTION | StorageType.SAVED)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def clean(self):
        """
            Clean artists
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("DELETE FROM artists WHERE artists.rowid NOT IN (\
                            SELECT album_artists.artist_id\
                            FROM album_artists) AND artists.rowid NOT IN (\
                                SELECT track_artists.artist_id\
                                FROM track_artists)")
