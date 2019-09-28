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

import itertools
from time import time

from lollypop.sqlcursor import SqlCursor
from lollypop.define import App, Type, OrderBy, StorageType
from lollypop.logger import Logger
from lollypop.utils import noaccents, get_default_storage_type, remove_static


class AlbumsDatabase:
    """
        Albums database helper
    """

    def __init__(self):
        """
            Init albums database object
        """
        self.__max_count = 1

    def add(self, album_name, mb_album_id, artist_ids,
            uri, loved, popularity, rate, synced, mtime, storage_type):
        """
            Add a new album to database
            @param album_name as str
            @param mb_album_id as str
            @param artist_ids as int
            @param uri as str
            @param loved as bool
            @param popularity as int
            @param rate as int
            @param synced as int
            @param mtime as int
            @param storage_type as int
            @return inserted rowid as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            result = sql.execute("INSERT INTO albums\
                                  (name, mb_album_id, no_album_artist,\
                                  uri, loved, popularity, rate, mtime, synced,\
                                  storage_type)\
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 (album_name, mb_album_id or None,
                                  artist_ids == [], uri, loved, popularity,
                                  rate, mtime, synced, storage_type))
            for artist_id in artist_ids:
                sql.execute("INSERT INTO album_artists\
                             (album_id, artist_id)\
                             VALUES (?, ?)", (result.lastrowid, artist_id))
            return result.lastrowid

    def add_artist(self, album_id, artist_id):
        """
            Add artist to track
            @param album_id as int
            @param artist_id as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            artist_ids = self.get_artist_ids(album_id)
            if artist_id not in artist_ids:
                sql.execute("INSERT INTO "
                            "album_artists (album_id, artist_id)"
                            "VALUES (?, ?)", (album_id, artist_id))

    def add_genre(self, album_id, genre_id):
        """
            Add genre to album
            @param album_id as int
            @param genre_id as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            genres = self.get_genre_ids(album_id)
            if genre_id not in genres:
                sql.execute("INSERT INTO\
                             album_genres (album_id, genre_id)\
                             VALUES (?, ?)",
                            (album_id, genre_id))

    def set_artist_ids(self, album_id, artist_ids):
        """
            Set artist id
            @param album_id as int
            @param artist_ids as [int]
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("DELETE FROM album_artists\
                        WHERE album_id=?", (album_id,))
            for artist_id in artist_ids:
                sql.execute("INSERT INTO album_artists\
                            (album_id, artist_id)\
                            VALUES (?, ?)", (album_id, artist_id))

    def set_synced(self, album_id, synced):
        """
            Set album synced
            @param album_id as int
            @param synced as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET synced=? WHERE rowid=?",
                        (synced, album_id))

    def set_mtime(self, album_id, mtime):
        """
            Set album mtime
            @param album_id as int
            @param mtime as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET mtime=? WHERE rowid=?",
                        (mtime, album_id))

    def set_loved(self, album_id, loved):
        """
            Set album loved
            @param album_id as int
            @param loved as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET loved=? WHERE rowid=?",
                        (loved, album_id))

    def set_rate(self, album_id, rate):
        """
            Set album rate
            @param album_id as int
            @param rate as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET rate=? WHERE rowid=?",
                        (rate, album_id))

    def set_year(self, album_id, year):
        """
            Set year
            @param album_id as int
            @param year as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET year=? WHERE rowid=?",
                        (year, album_id))

    def set_timestamp(self, album_id, timestamp):
        """
            Set timestamp
            @param album_id as int
            @param timestamp as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET timestamp=? WHERE rowid=?",
                        (timestamp, album_id))

    def set_uri(self, album_id, uri):
        """
            Set album uri for album id
            @param album_id as int
            @param uri as string
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET uri=? WHERE rowid=?",
                        (uri, album_id))

    def set_storage_type(self, album_id, storage_type):
        """
            Set storage type
            @param album_id as int
            @param storage_type as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET storage_type=?\
                         WHERE rowid=?",
                        (storage_type, album_id))

    def set_popularity(self, album_id, popularity):
        """
            Set popularity
            @param album_id as int
            @param popularity as int
        """
        with SqlCursor(App().db, True) as sql:
            try:
                sql.execute("UPDATE albums set popularity=? WHERE rowid=?",
                            (popularity, album_id))
            except:  # Database is locked
                pass

    def get_synced_ids(self, index):
        """
            Get synced album ids
            @param index as int => device index from gsettings
        """
        with SqlCursor(App().db) as sql:
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums, artists, album_artists\
                       WHERE album_artists.album_id = albums.rowid\
                       AND (album_artists.artist_id = artists.rowid\
                            OR album_artists.artist_id=?)\
                       AND synced & (1 << ?) AND albums.storage_type & ?"
            order = " ORDER BY artists.sortname\
                     COLLATE NOCASE COLLATE LOCALIZED,\
                     albums.timestamp,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
            filters = (Type.COMPILATIONS, index, StorageType.COLLECTION)
            result = sql.execute(request + order, filters)
            return list(itertools.chain(*result))

    def get_synced(self, album_id):
        """
            Get album synced status
            @param album_id as int
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT synced FROM albums WHERE\
                                 rowid=?", (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_loved(self, album_id):
        """
            Get album loved
            @param album_id as int
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT loved FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_storage_type(self, album_id):
        """
            Get storage type
            @param album_id as int
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT storage_type FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return StorageType.NONE

    def get_for_storage_type(self, storage_type, limit):
        """
            Get albums by storage type
            @param storage_type as StorageType
            @param limit as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            filters = (storage_type, limit)
            request = "SELECT rowid\
                       FROM albums\
                       WHERE storage_type=? ORDER BY RANDOM() LIMIT ?"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_newer_for_storage_type(self, storage_type, timestamp):
        """
            Get albums newer than timestamp for storage type
            @param storage_type as StorageType
            @param timestamp as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            filters = (storage_type, timestamp)
            request = "SELECT rowid FROM albums\
                       WHERE storage_type=? and mtime>?"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_oldest_for_storage_type(self, storage_type, limit):
        """
            Get albums by storage type
            @param storage_type as StorageType
            @param limit as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            filters = (storage_type, limit)
            request = "SELECT rowid FROM albums\
                       WHERE storage_type=? ORDER BY mtime ASC LIMIT ?"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_count_for_storage_type(self, storage_type):
        """
            Get albums count for storage type
            @param storage_type as StorageType
            @return int
        """
        with SqlCursor(App().db) as sql:
            filters = (storage_type,)
            request = "SELECT COUNT(*) FROM albums WHERE storage_type=?"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_rate(self, album_id):
        """
            Get album rate
            @param album_id as int
            @return rate as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rate FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v:
                return v[0]
            return 0

    def get_popularity(self, album_id):
        """
            Get popularity
            @param album_id as int
            @return popularity as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT popularity FROM albums WHERE\
                                 rowid=?", (album_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def set_more_popular(self, album_id, pop_to_add):
        """
            Increment popularity field for album id
            @param album_id as int
            @param pop_to_add as int
            @raise sqlite3.OperationalError on db update
        """
        with SqlCursor(App().db, True) as sql:
            result = sql.execute("SELECT popularity from albums WHERE rowid=?",
                                 (album_id,))
            pop = result.fetchone()
            if pop:
                current = pop[0]
            else:
                current = 0
            current += pop_to_add
            sql.execute("UPDATE albums set popularity=? WHERE rowid=?",
                        (current, album_id))

    def get_higher_popularity(self):
        """
            Get higher available popularity
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT popularity\
                                  FROM albums\
                                  ORDER BY POPULARITY DESC LIMIT 1")
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_avg_popularity(self):
        """
            Return avarage popularity
            @return avarage popularity as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT AVG(popularity)\
                                  FROM (SELECT popularity\
                                        FROM albums\
                                        ORDER BY POPULARITY DESC LIMIT 1000)")
            v = result.fetchone()
            if v and v[0] > 5:
                return v[0]
            return 5

    def get_id(self, album_name, mb_album_id, artist_ids):
        """
            Get non compilation album id
            @param album_name as str
            @param mb_album_id as str
            @param artist_ids as [int]
            @return int
        """
        with SqlCursor(App().db) as sql:
            filters = (album_name,)
            if artist_ids:
                request = "SELECT albums.rowid FROM albums, album_artists\
                           WHERE name=? COLLATE NOCASE "
                if mb_album_id:
                    request += "AND albums.mb_album_id=? "
                    filters += (mb_album_id,)
                else:
                    request += "AND albums.mb_album_id IS NULL "
                request += "AND no_album_artist=0 AND\
                            album_artists.album_id=albums.rowid AND (1=0 "
                filters += tuple(artist_ids)
                for artist_id in artist_ids:
                    request += "OR artist_id=? "
                request += ")"
            else:
                request = "SELECT rowid FROM albums\
                           WHERE name=?\
                           AND no_album_artist=1"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_id_by(self, album_name, artist_ids):
        """
            Get album for name and artists
            @param album_name as escaped str
            @param artist_ids as [int]
            @return int
        """
        with SqlCursor(App().db) as sql:
            filters = (album_name,)
            request = "SELECT albums.rowid FROM albums, album_artists\
                       WHERE sql_escape(name)=? COLLATE NOCASE AND\
                       album_artists.album_id=albums.rowid AND (1=0 "
            filters += tuple(artist_ids)
            for artist_id in artist_ids:
                request += "OR artist_id=? "
            request += ")"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def set_genre_ids(self, album_id, genre_ids):
        """
            Set genre_ids for album
            @param album_id as int
            @param genre_ids as [int]
        """
        with SqlCursor(App().db) as sql:
            request = "DELETE from album_genres\
                       WHERE album_genres.album_id=?"
            sql.execute(request, (album_id,))
            for genre_id in genre_ids:
                request = "INSERT INTO album_genres (album_id, genre_id)\
                           VALUES (?, ?)"
                sql.execute(request, (album_id, genre_id))

    def get_genre_ids(self, album_id):
        """
            Get genre ids
            @param album_id as int
            @return Genres id as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT genre_id FROM album_genres\
                                  WHERE album_id=?", (album_id,))
            return list(itertools.chain(*result))

    def get_name(self, album_id):
        """
            Get album name for album id
            @param album_id as int
            @return str
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT name FROM albums where rowid=?",
                                 (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_artists(self, album_id):
        """
            Get artist names
            @param album_id as int
            @return artists as [str]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT artists.name\
                                 FROM artists, album_artists\
                                 WHERE album_artists.album_id=?\
                                 AND album_artists.artist_id=artists.rowid",
                                 (album_id,))
            return list(itertools.chain(*result))

    def get_artist_ids(self, album_id):
        """
            Get album artist id
            @param album_id
            @return artist ids as [int]artist_ids
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT artist_id\
                                  FROM album_artists\
                                  WHERE album_id=?",
                                 (album_id,))
            return list(itertools.chain(*result))

    def get_mb_album_id(self, album_id):
        """
            Get MusicBrainz album id for album id
            @param album_id as int
            @return MusicBrainz album id as str
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT mb_album_id FROM albums\
                                  WHERE rowid=?", (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return -1

    def get_mtime(self, album_id):
        """
            Get modification time
            @param album_id as int
            @return modification time as int
        """
        with SqlCursor(App().db) as sql:
            request = "SELECT mtime FROM albums WHERE albums.rowid=?"
            result = sql.execute(request, (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_year(self, album_id):
        """
            Get album year
            @param album_id as int
            @return album year as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT year FROM albums where rowid=?",
                                 (album_id,))
            v = result.fetchone()
            if v and v[0]:
                return v[0]
            return None

    def get_uri(self, album_id):
        """
            Get album uri for album id
            @param album_id as int
            @return Album uri as string
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT uri FROM albums WHERE rowid=?",
                                 (album_id,))
            uri = ""
            v = result.fetchone()
            if v is not None:
                uri = v[0]
            return uri

    def get_uri_count(self, uri):
        """
            Count album having uri as album uri
            @param uri as str
            @return count as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT COUNT(uri) FROM albums WHERE uri=?",
                                 (uri,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 1

    def get_uris(self):
        """
            Get all albums uri
            @return [str]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT uri FROM albums")
            return list(itertools.chain(*result))

    def get_rated(self, limit=100):
        """
            Get albums with user rating >= 4
            @param limit as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums\
                       WHERE rate>=4 AND loved != -1 AND storage_type & ?\
                       ORDER BY popularity DESC LIMIT ?"
            result = sql.execute(request, (storage_type, limit))
            return list(itertools.chain(*result))

    def get_populars(self, limit=100):
        """
            Get popular albums
            @param limit as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            request = "SELECT DISTINCT albums.rowid FROM albums\
                       WHERE popularity!=0 AND loved != -1 AND\
                       storage_type & ?\
                       ORDER BY popularity DESC LIMIT ?"
            result = sql.execute(request,
                                 (storage_type, limit))
            return list(itertools.chain(*result))

    def get_populars_at_the_moment(self, limit=100):
        """
            Get popular albums at the moment
            @param limit as int
            @return [int]
        """
        # Last month
        timestamp = time() - 2419200
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            request = "SELECT DISTINCT albums.rowid FROM albums, tracks\
                       WHERE albums.storage_type & ? AND\
                             tracks.ltime > ? AND\
                             albums.rowid = tracks.album_id\
                       ORDER BY albums.popularity DESC LIMIT ?"
            result = sql.execute(request, (storage_type, timestamp, limit))
            return list(itertools.chain(*result))

    def get_loved_albums(self):
        """
            Get loved albums
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            request = "SELECT DISTINCT albums.rowid\
                       FROM albums\
                       WHERE loved=1 AND\
                       storage_type & ? ORDER BY popularity DESC"
            result = sql.execute(request, (storage_type,))
            return list(itertools.chain(*result))

    def get_recents(self):
        """
            Return recent albums
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            request = "SELECT DISTINCT albums.rowid FROM albums\
                       WHERE albums.loved != -1 AND\
                       albums.storage_type & ?\
                       ORDER BY mtime DESC LIMIT 100"
            result = sql.execute(request, (storage_type,))
            return list(itertools.chain(*result))

    def get_randoms(self, genre_id=None, limit=100):
        """
            Return random albums
            @param genre_id as int
            @param limit as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            albums = []
            storage_type = get_default_storage_type()
            if genre_id is not None:
                filter = (storage_type, genre_id, limit)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_genres\
                           WHERE albums.loved != -1 AND\
                                 albums.storage_type & ? AND\
                                 album_genres.album_id = albums.rowid AND\
                                 album_genres.genre_id = ?\
                                 ORDER BY random() LIMIT ?"
            else:
                filter = (storage_type, limit)
                request = "SELECT DISTINCT rowid FROM albums\
                           WHERE loved != -1 AND\
                           storage_type & ? ORDER BY random() LIMIT ?"
            result = sql.execute(request, filter)
            albums = list(itertools.chain(*result))
            return albums

    def get_disc_names(self, album_id, disc):
        """
            Get disc names
            @param album_id as int
            @param disc as int
            @return name as str
        """
        with SqlCursor(App().db) as sql:
            request = "SELECT DISTINCT discname\
                       FROM tracks\
                       WHERE tracks.album_id=?\
                       AND tracks.discnumber=?\
                       AND discname!=''"
            filters = (album_id, disc)
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_discs(self, album_id, genre_ids):
        """
            Get disc numbers
            @param album_id as int
            @param genre_ids as [int]
            @return [disc as int]
        """
        genre_ids = remove_static(genre_ids)
        with SqlCursor(App().db) as sql:
            filters = (album_id,)
            filters += tuple(genre_ids)
            request = "SELECT DISTINCT discnumber\
                       FROM tracks, track_genres\
                       WHERE tracks.album_id=?\
                       AND track_genres.track_id = tracks.rowid"
            if genre_ids:
                request += " AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
            request += " ORDER BY discnumber"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_track_uris(self, album_id):
        """
            Get track uris for album id/disc
            @param album_id as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            request = "SELECT DISTINCT tracks.uri\
                       FROM tracks WHERE album_id=?"
            result = sql.execute(request, (album_id,))
            return list(itertools.chain(*result))

    def get_disc_track_ids(self, album_id, genre_ids, artist_ids,
                           disc, disallow_ignored_tracks):
        """
            Get tracks ids for album id disc

            @param album_id as int
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param disc as int
            @param disallow_ignored_tracks as bool
            @return [int]
        """
        genre_ids = remove_static(genre_ids)
        artist_ids = remove_static(artist_ids)
        with SqlCursor(App().db) as sql:
            filters = (album_id, disc)
            request = "SELECT DISTINCT tracks.rowid\
                       FROM tracks"
            if genre_ids:
                request += ", track_genres"
                filters += tuple(genre_ids)
            if artist_ids:
                request += ", track_artists"
                filters += tuple(artist_ids)
            request += " WHERE album_id=?\
                       AND discnumber=?"
            if genre_ids:
                request += " AND track_genres.track_id = tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
            if artist_ids:
                request += " AND track_artists.track_id=tracks.rowid AND ("
                for artist_id in artist_ids:
                    request += "track_artists.artist_id=? OR "
                request += "1=0)"
            if disallow_ignored_tracks:
                request += " AND tracks.loved != -1"
            request += " ORDER BY discnumber, tracknumber, tracks.name"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_tracks_count(self, album_id, genre_ids, artist_ids):
        """
            Get tracks ids for album
            @param album_id as int
            @param genre_ids as [int]
            @param artist_ids as [int]
            @return [int]
        """
        genre_ids = remove_static(genre_ids)
        artist_ids = remove_static(artist_ids)
        with SqlCursor(App().db) as sql:
            filters = (album_id,)
            request = "SELECT COUNT(*) FROM tracks"
            if genre_ids:
                request += ", track_genres"
                filters += tuple(genre_ids)
            if artist_ids:
                request += ", track_artists"
                filters += tuple(artist_ids)
            request += " WHERE album_id=?"
            if genre_ids:
                request += " AND track_genres.track_id = tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
            if artist_ids:
                request += " AND track_artists.track_id=tracks.rowid AND ("
                for artist_id in artist_ids:
                    request += "track_artists.artist_id=? OR "
                request += "1=0)"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None and v[0] > 0:
                return v[0]
            return 1

    def get_id_by_uri(self, uri):
        """
            Get album id for uri
            @param uri as str
            @return id as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM albums\
                                  WHERE uri=?",
                                 (uri,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_ids(self, artist_ids, genre_ids, ignore=False, orderby=None):
        """
            Get albums ids
            @param artist_ids as [int]
            @param genre_ids as [int]
            @param ignore as bool => ignore albums with loved == 1
            @param orderby as OrderBy
            @return albums ids as [int]
        """
        genre_ids = remove_static(genre_ids)
        artist_ids = remove_static(artist_ids)
        if orderby is None:
            orderby = App().settings.get_enum("orderby")
        if artist_ids or orderby == OrderBy.ARTIST:
            order = " ORDER BY artists.sortname\
                     COLLATE NOCASE COLLATE LOCALIZED,\
                     albums.timestamp,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.NAME:
            order = " ORDER BY albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.YEAR_DESC:
            order = " ORDER BY albums.timestamp DESC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.YEAR_ASC:
            order = " ORDER BY albums.timestamp ASC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        else:
            order = " ORDER BY albums.popularity DESC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"

        with SqlCursor(App().db) as sql:
            result = []
            storage_type = get_default_storage_type()
            # Get albums for all artists
            if not artist_ids and not genre_ids:
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_artists, artists\
                           WHERE albums.rowid = album_artists.album_id AND\
                           albums.storage_type & ? AND\
                           artists.rowid = album_artists.artist_id"
                if ignore:
                    request += " AND albums.loved != -1"
                request += order
                result = sql.execute(request, (storage_type,))
            # Get albums for genres
            elif not artist_ids:
                filters = (storage_type,)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid FROM albums,\
                           album_genres, album_artists, artists\
                           WHERE albums.rowid = album_artists.album_id AND\
                           artists.rowid = album_artists.artist_id AND\
                           albums.storage_type & ? AND\
                           album_genres.album_id=albums.rowid AND ( "
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0)"
                if ignore:
                    request += " AND albums.loved != -1"
                request += order
                result = sql.execute(request, filters)
            # Get albums for artist
            elif not genre_ids:
                filters = (storage_type,)
                filters += tuple(artist_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_artists, artists\
                           WHERE album_artists.album_id=albums.rowid AND\
                           albums.storage_type & ? AND\
                           artists.rowid = album_artists.artist_id AND ("
                for artist_id in artist_ids:
                    request += "artists.rowid=? OR "
                request += "1=0)"
                if ignore:
                    request += " AND albums.loved != -1"
                request += order
                result = sql.execute(request, filters)
            # Get albums for artist id and genre id
            else:
                filters = (storage_type,)
                filters += tuple(artist_ids)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_genres, album_artists, artists\
                           WHERE album_genres.album_id=albums.rowid AND\
                           artists.rowid = album_artists.artist_id AND\
                           albums.storage_type & ? AND\
                           album_artists.album_id=albums.rowid AND ("
                for artist_id in artist_ids:
                    request += "artists.rowid=? OR "
                request += "1=0) AND ("
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0)"
                if ignore:
                    request += " AND albums.loved != -1"
                request += order
                result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_compilation_ids(self, genre_ids, ignore=False):
        """
            Get all compilations
            @param genre_ids as [int]
            @param ignore as bool => ignore albums with loved == 1
            @return [int]
        """
        genre_ids = remove_static(genre_ids)
        with SqlCursor(App().db) as sql:
            order = " ORDER BY albums.name, albums.timestamp"
            result = []
            storage_type = get_default_storage_type()
            # Get all compilations
            if not genre_ids or genre_ids[0] == Type.ALL:
                filters = (storage_type, Type.COMPILATIONS)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_artists\
                           WHERE albums.storage_type & ?\
                           AND album_artists.artist_id=?\
                           AND album_artists.album_id=albums.rowid"
                if ignore:
                    request += " AND albums.loved != -1"
                request += order
                result = sql.execute(request, filters)
            # Get compilation for genre id
            else:
                filters = (storage_type, Type.COMPILATIONS)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT albums.rowid\
                           FROM albums, album_genres, album_artists\
                           WHERE album_genres.album_id=albums.rowid\
                           AND albums.storage_type & ?\
                           AND albums.loved != -1\
                           AND album_artists.album_id=albums.rowid\
                           AND album_artists.artist_id=? AND ( "
                for genre_id in genre_ids:
                    request += "album_genres.genre_id=? OR "
                request += "1=0)"
                if ignore:
                    request += " AND albums.loved != -1"
                request += order
                result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_duration(self, album_id, genre_ids):
        """
            Album duration in seconds
            @param album_id as int
            @param genre_ids as [int]
            @return album duration as int
        """
        genre_ids = remove_static(genre_ids)
        with SqlCursor(App().db) as sql:
            if genre_ids and genre_ids[0] > 0:
                filters = (album_id,)
                filters += tuple(genre_ids)
                request = "SELECT SUM(duration)\
                           FROM tracks, track_genres\
                           WHERE tracks.album_id=?\
                           AND track_genres.track_id = tracks.rowid AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
                result = sql.execute(request, filters)
            else:
                result = sql.execute("SELECT SUM(duration) FROM tracks\
                                      WHERE album_id=?", (album_id,))
            v = result.fetchone()
            if v and v[0] is not None:
                return v[0]
            return 0

    def get_genres(self, album_id):
        """
            Return genres for album
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT genres.name\
                                  FROM albums, album_genres, genres\
                                  WHERE albums.rowid = ?\
                                  AND album_genres.album_id = albums.rowid\
                                  AND album_genres.genre_id = genres.rowid",
                                 (album_id,))
            return list(itertools.chain(*result))

    def get_never_listened_to(self):
        """
            Return random albums never listened to
            @return album ids as [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            result = sql.execute("SELECT DISTINCT albums.rowid\
                                  FROM albums, tracks\
                                  WHERE albums.loved != -1 AND\
                                  albums.storage_type & ? AND\
                                  albums.rowid=tracks.album_id\
                                  AND albums.popularity = 0\
                                  ORDER BY random() LIMIT 100",
                                 (storage_type,))
            return list(itertools.chain(*result))

    def get_years(self):
        """
            Return all albums years and if unknown album exists
            @return ([int], bool)
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT albums.year FROM albums")
            years = []
            unknown = False
            for year in list(itertools.chain(*result)):
                if year is None:
                    unknown = True
                elif year not in years:
                    years.append(year)
            return (years, unknown)

    def get_albums_for_year(self, year, limit=-1):
        """
            Return albums for year
            @param year as int
            @param limit as int
            @return album ids as [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            if limit != -1:
                result = sql.execute("SELECT albums.rowid\
                                      FROM albums\
                                      WHERE year=? AND storage_type & ?\
                                      ORDER BY random() LIMIT ?",
                                     (year, storage_type, limit))
            else:
                order = " ORDER BY artists.sortname\
                         COLLATE NOCASE COLLATE LOCALIZED,\
                         albums.timestamp,\
                         albums.name\
                         COLLATE NOCASE COLLATE LOCALIZED"
                if year == Type.NONE:
                    request = "SELECT DISTINCT albums.rowid\
                               FROM albums, album_artists, artists\
                               WHERE albums.rowid=album_artists.album_id AND\
                               artists.rowid=album_artists.artist_id AND\
                               albums.year is null AND albums.storage_type & ?"
                    filter = (storage_type,)
                else:
                    request = "SELECT DISTINCT albums.rowid\
                               FROM albums, album_artists, artists\
                               WHERE albums.rowid=album_artists.album_id AND\
                               artists.rowid=album_artists.artist_id AND\
                               albums.year=? AND albums.storage_type & ?"
                    filter = (year, storage_type)
                request += order
                result = sql.execute(request, filter)
            return list(itertools.chain(*result))

    def get_compilations_for_year(self, year, limit=-1):
        """
            Return compilations for year
            @param year as int
            @param limit as int
            @return album ids as [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            if limit != -1:
                result = sql.execute("SELECT albums.rowid\
                                      FROM albums, album_artists\
                                      WHERE album_artists.artist_id=?\
                                      AND album_artists.album_id=albums.rowid\
                                      AND albums.storage_type & ?\
                                      AND albums.year=? LIMIT ?",
                                     (Type.COMPILATIONS, year,
                                      storage_type, limit))
            else:
                order = " ORDER BY albums.timestamp, albums.name\
                         COLLATE NOCASE COLLATE LOCALIZED"
                if year == Type.NONE:
                    request = "SELECT DISTINCT albums.rowid\
                               FROM albums, album_artists\
                               WHERE album_artists.artist_id=?\
                               AND album_artists.album_id=albums.rowid\
                               AND albums.storage_type & ?\
                               AND albums.year is null"
                    filter = (Type.COMPILATIONS, storage_type)
                else:
                    request = "SELECT DISTINCT albums.rowid\
                               FROM albums, album_artists\
                               WHERE album_artists.artist_id=?\
                               AND album_artists.album_id=albums.rowid\
                               AND albums.storage_type & ?\
                               AND albums.year=?"
                    filter = (Type.COMPILATIONS, storage_type, year)
                request += order
                result = sql.execute(request, filter)
            return list(itertools.chain(*result))

    def search(self, searched, storage_type):
        """
            Search for albums looking like string
            @param searched as str
            @param storage_type as StorageType
            @return album ids as [int]
        """
        with SqlCursor(App().db) as sql:
            no_accents = noaccents(searched)
            items = []
            # From best filter to worst filter
            for filter in [(no_accents + "%", storage_type),
                           ("%" + no_accents, storage_type),
                           ("%" + no_accents + "%", storage_type)]:
                request = "SELECT albums.rowid FROM albums\
                           WHERE noaccents(name) LIKE ?\
                           AND albums.storage_type & ? LIMIT 25"
                result = sql.execute(request, filter)
                items += list(itertools.chain(*result))
            for filter in [(no_accents + "%", storage_type),
                           ("%" + no_accents, storage_type),
                           ("%" + no_accents + "%", storage_type)]:
                request = "SELECT DISTINCT albums.rowid\
                       FROM albums, album_artists, artists\
                       WHERE album_artists.artist_id=artists.rowid AND\
                       album_artists.album_id=albums.rowid AND\
                       noaccents(artists.name) LIKE ? AND\
                       albums.storage_type & ? LIMIT 25"
                result = sql.execute(request, filter)
                items += list(itertools.chain(*result))
            return list(set(items))

    def calculate_artist_ids(self, album_id):
        """
            Calculate artist ids based on tracks
            @WARNING Be sure album already have a track
            @param album_id as int
            @return artist_ids as [int]
        """
        ret = []
        try:
            with SqlCursor(App().db) as sql:
                request = "SELECT DISTINCT rowid\
                           FROM tracks WHERE album_id=?"
                result = sql.execute(request, (album_id,))
                for track_id in list(itertools.chain(*result)):
                    artist_ids = App().tracks.get_artist_ids(track_id)
                    # Check if previous track and
                    # track do not have same artists
                    if ret:
                        if not set(ret) & set(artist_ids):
                            return [Type.COMPILATIONS]
                    ret = artist_ids
        except Exception as e:
            Logger.error("AlbumsDatabase::calculate_artist_ids(): %s" % e)
        return ret

    def remove_device(self, index):
        """
            Remove device from DB
            @param index as int => device index
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE albums SET synced = synced & ~(1<<?)",
                        (index,))

    def count(self):
        """
            Count albums
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT COUNT(1) FROM albums\
                                  WHERE storage_type & ?",
                                 ((StorageType.COLLECTION |
                                   StorageType.SAVED,)))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def clean(self, commit=True):
        """
            Clean albums
            @param commit as bool
        """
        with SqlCursor(App().db, commit) as sql:
            sql.execute("DELETE FROM albums WHERE albums.rowid NOT IN (\
                            SELECT tracks.album_id FROM tracks)")
            sql.execute("DELETE FROM album_genres\
                         WHERE album_genres.album_id NOT IN (\
                            SELECT albums.rowid FROM albums)")
            sql.execute("DELETE FROM album_artists\
                         WHERE album_artists.album_id NOT IN (\
                            SELECT albums.rowid FROM albums)")

    @property
    def max_count(self):
        """
            Get MAX(COUNT(tracks)) for albums
        """
        return self.__max_count

    def update_max_count(self):
        """
            Update MAX(COUNT(tracks)) for albums
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT MAX(num_tracks)\
                                  FROM (SELECT COUNT(t.rowid)\
                                  AS num_tracks FROM albums\
                                  INNER JOIN tracks t\
                                  ON albums.rowid=t.album_id\
                                  GROUP BY albums.rowid)")
            v = result.fetchone()
            if v and v[0] is not None:
                self.__max_count = v[0]

#######################
# PRIVATE             #
#######################
