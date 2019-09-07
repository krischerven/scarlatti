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
from time import time

from lollypop.sqlcursor import SqlCursor
from lollypop.define import App, OrderBy, StorageType, Type
from lollypop.utils import noaccents, remove_static, get_default_storage_type


class TracksDatabase:
    """
        All functions take a sqlite cursor as last parameter,
        set another one if you"re in a thread
    """

    def __init__(self):
        """
            Init tracks database object
        """
        pass

    def add(self, name, uri, duration, tracknumber, discnumber, discname,
            album_id, year, timestamp, popularity, rate, loved, ltime, mtime,
            mb_track_id, bpm, storage_type):
        """
            Add a new track to database
            @param name as string
            @param uri as string,
            @param duration as int
            @param tracknumber as int
            @param discnumber as int
            @param discname as str
            @param album_id as int
            @param year as int
            @param timestamp as int
            @param popularity as int
            @param rate as int
            @param loved as bool
            @param ltime as int
            @param mtime as int
            @param mb_track_id as str
            @param bpm as double
            @return inserted rowid as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            result = sql.execute(
                "INSERT INTO tracks (name, uri, duration, tracknumber,\
                discnumber, discname, album_id,\
                year, timestamp, popularity, rate, loved,\
                ltime, mtime, mb_track_id, bpm, storage_type) VALUES\
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    name,
                    uri,
                    duration,
                    tracknumber,
                    discnumber,
                    discname,
                    album_id,
                    year,
                    timestamp,
                    popularity,
                    rate,
                    loved,
                    ltime,
                    mtime,
                    mb_track_id,
                    bpm,
                    storage_type))
            return result.lastrowid

    def add_artist(self, track_id, artist_id):
        """
            Add artist to track
            @param track_id as int
            @param artist_id as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            artists = self.get_artist_ids(track_id)
            if artist_id not in artists:
                sql.execute("INSERT INTO "
                            "track_artists (track_id, artist_id)"
                            "VALUES (?, ?)", (track_id, artist_id))

    def add_genre(self, track_id, genre_id):
        """
            Add genre to track
            @param track_id as int
            @param genre_id as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            genres = self.get_genre_ids(track_id)
            if genre_id not in genres:
                sql.execute("INSERT INTO\
                             track_genres (track_id, genre_id)\
                             VALUES (?, ?)",
                            (track_id, genre_id))

    def get_ids(self):
        """
            Return all internal track ids
            @return track ids as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks")
            return list(itertools.chain(*result))

    def get_ids_for_name(self, name):
        """
            Return tracks ids with name
            @param name as str
            @return track id as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM tracks WHERE noaccents(name)=?\
                                  COLLATE NOCASE",
                                 (noaccents(name),))
            return list(itertools.chain(*result))

    def get_id_by_uri(self, uri):
        """
            Return track id for uri
            @param uri as str
            @return track id as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks WHERE uri=?",
                                 (uri,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_id_by_basename_duration(self, basename, duration):
        """
            Get track id by basename
            @param basename as str
            @param duration as int
            @return track_id as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE uri like ? AND duration=?",
                                 ("%" + basename, duration))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_id_by(self, name, album_id, artist_ids=[]):
        """
            Get track for name, album and artists
            @param name as escaped str
            @param album_id as int
            @param artist_ids as [int]
            @return track id as int
        """
        with SqlCursor(App().db) as sql:
            if artist_ids:
                filters = (name, album_id) + tuple(artist_ids)
                request = "SELECT tracks.rowid FROM tracks\
                           WHERE sql_escape(name) = ? COLLATE NOCASE\
                           AND album_id = ?\
                           AND EXISTS (\
                                SELECT rowid\
                                FROM track_artists\
                                WHERE track_artists.track_id=tracks.rowid\
                                AND ("
                for artist_id in artist_ids:
                    request += " track_artists.artist_id=? OR"
                request += " 1=0))"
            else:
                filters = (name, album_id)
                request = "SELECT tracks.rowid FROM tracks\
                           WHERE sql_escape(name) = ? COLLATE NOCASE\
                           AND album_id = ?"
            result = sql.execute(request, filters)
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_ids_by_artist(self, artist_id):
        """
            Return track id for artist
            @param artist_id as int
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            filters = (artist_id,)
            request = "SELECT tracks.rowid FROM tracks, track_artists\
                       WHERE track_artists.artist_id=? AND\
                       tracks.rowid = track_artists.track_id"
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_name(self, track_id):
        """
            Get track name for track id
            @param track_id as int
            @return Name as string
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT name FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_year(self, track_id):
        """
            Get track year
            @param track_id as int
            @return year as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT year FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v and v[0]:
                return v[0]
            return None

    def get_storage_type(self, track_id):
        """
            Get storage type
            @param track_id as int
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT storage_type FROM tracks WHERE\
                                 rowid=?", (track_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_timestamp(self, track_id):
        """
            Get track timestamp
            @param track_id as int
            @return timestamp as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT timestamp FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v and v[0]:
                return v[0]
            return None

    def get_year_for_album(self, album_id):
        """
            Get album year based on tracks
            Use most used year by tracks
            @param album_id as int
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT year, COUNT(year) AS occurrence\
                                  FROM tracks\
                                  WHERE tracks.album_id=?\
                                  GROUP BY year\
                                  ORDER BY occurrence DESC\
                                  LIMIT 1", (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_timestamp_for_album(self, album_id):
        """
            Get album timestamp based on tracks
            Use most used timestamp by tracks
            @param album_id as int
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT timestamp,\
                                  COUNT(timestamp) AS occurrence\
                                  FROM tracks\
                                  WHERE tracks.album_id=?\
                                  GROUP BY timestamp\
                                  ORDER BY occurrence DESC\
                                  LIMIT 1", (album_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_rate(self, track_id):
        """
            Get track rate
            @param track_id as int
            @return rate as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rate FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v:
                return v[0]
            return 0

    def get_uri(self, track_id):
        """
            Get track uri for track id
            @param track_id as int
            @return uri as string
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT uri FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def set_uri(self, track_id, uri):
        """
            Set track uri
            @param track_id as int
            @param uri as string
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks SET uri=?\
                         WHERE rowid=?",
                        (uri, track_id))

    def set_storage_type(self, track_id, storage_type):
        """
            Set storage type
            @param track_id as int
            @param storage_type as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks SET storage_type=?\
                         WHERE rowid=?",
                        (storage_type, track_id))

    def set_rate(self, track_id, rate):
        """
            Set track rate
            @param track_id as int
            @param rate as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks SET rate=?\
                         WHERE rowid=?",
                        (rate, track_id))

    def get_album_id(self, track_id):
        """
            Get album id for track id
            @param track_id as int
            @return album id as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT album_id FROM tracks WHERE rowid=?",
                                 (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return -1

    def get_mb_track_id(self, track_id):
        """
            Get MusicBrainz recording id for track id
            @param track_id as int
            @return recording id as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT mb_track_id FROM tracks\
                                  WHERE rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return -1

    def get_album_name(self, track_id):
        """
            Get album name for track id
            @param track_id as int
            @return album name as str
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT albums.name from albums,tracks\
                                  WHERE tracks.rowid=? AND\
                                  tracks.album_id=albums.rowid", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return _("Unknown")

    def get_artist_ids(self, track_id):
        """
            Get artist ids
            @param track_id as int
            @return artist ids as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT artist_id FROM track_artists\
                                  WHERE track_id=?", (track_id,))
            return list(itertools.chain(*result))

    def get_mb_artist_ids(self, track_id):
        """
            Get MusicBrainz artist ids
            @param track_id as int
            @return artist ids as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT mb_artist_id\
                                  FROM artists, track_artists\
                                  WHERE track_artists.track_id=?\
                                  AND track_artists.artist_id=artists.rowid",
                                 (track_id,))
            return list(itertools.chain(*result))

    def get_artists(self, track_id):
        """
            Get artist names
            @param track_id as int
            @return artists as [str]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT name FROM artists, track_artists\
                                  WHERE track_artists.track_id=?\
                                  AND track_artists.artist_id=artists.rowid",
                                 (track_id,))
            return list(itertools.chain(*result))

    def get_genre_ids(self, track_id):
        """
            Get genre ids
            @param track_id as int
            @return genre ids as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT genre_id FROM track_genres\
                                  WHERE track_id=?", (track_id,))
            return list(itertools.chain(*result))

    def get_genres(self, track_id):
        """
            Get genres
            @param track_id as int
            @return [str]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT name FROM genres, track_genres\
                                  WHERE track_genres.track_id=?\
                                  AND track_genres.genre_id=genres.rowid",
                                 (track_id,))
            return list(itertools.chain(*result))

    def get_album_ids(self, artist_ids, genre_ids, ignore=False):
        """
            Get albums ids
            @param artist_ids as [int]
            @param genre_ids as [int]
            @return albums ids as [int]
            @param ignore as bool
        """
        genre_ids = remove_static(genre_ids)
        artist_ids = remove_static(artist_ids)
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
        else:
            order = " ORDER BY albums.popularity DESC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"

        with SqlCursor(App().db) as sql:
            result = []
            storage_type = get_default_storage_type()
            # Get albums for all artists
            if not artist_ids and not genre_ids:
                request = "SELECT DISTINCT tracks.album_id\
                           FROM tracks, track_artists, artists, albums\
                           WHERE tracks.rowid = track_artists.track_id AND\
                           artists.rowid = track_artists.artist_id AND\
                           track.storage_type & ? AND\
                           album_id=tracks.album_id"
                if ignore:
                    request += " AND tracks.loved != -1"
                request += order
                result = sql.execute(request, (storage_type,))
            # Get albums for genres
            elif not artist_ids:
                filters = (storage_type,)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT tracks.album_id FROM tracks,\
                           album, track_genres, track_artists, artists\
                           WHERE tracks.rowid = track_artists.track_id AND\
                           artists.rowid = track_artists.artist_id  AND\
                           album_id=tracks.album_id AND\
                           track.storage_type & ? AND\
                           track_genres.track_id=tracks.rowid AND ( "
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
                if ignore:
                    request += " AND tracks.loved != -1"
                request += order
                result = sql.execute(request, filters)
            # Get albums for artist
            elif not genre_ids:
                filters = (storage_type,)
                filters += tuple(artist_ids)
                request = "SELECT DISTINCT tracks.album_id\
                           FROM tracks, track_artists, artists, albums\
                           WHERE track_artists.track_id=tracks.rowid AND\
                           album_id=tracks.album_id AND\
                           track.storage_type & ? AND\
                           artists.rowid = track_artists.artist_id AND ("
                for artist_id in artist_ids:
                    request += "artists.rowid=? OR "
                request += "1=0)"
                if ignore:
                    request += " AND tracks.loved != -1"
                request += order
                result = sql.execute(request, filters)
            # Get albums for artist id and genre id
            else:
                filters = (storage_type,)
                filters += tuple(artist_ids)
                filters += tuple(genre_ids)
                request = "SELECT DISTINCT tracks.album_id\
                           FROM tracks, track_genres, albums,\
                           track_artists, artists\
                           WHERE track_genres.track_id=tracks.rowid AND\
                           artists.rowid = track_artists.artist_id AND\
                           album_id=tracks.album_id AND\
                           track.storage_type & ? AND\
                           track_artists.track_id=tracks.rowid AND ("
                for artist_id in artist_ids:
                    request += "artists.rowid=? OR "
                request += "1=0) AND ("
                for genre_id in genre_ids:
                    request += "track_genres.genre_id=? OR "
                request += "1=0)"
                if ignore:
                    request += " AND tracks.loved != -1"
                request += order
                result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get_mtimes(self):
        """
            Get mtime for tracks
            WARNING: Should be called before anything is shown on screen
            @return dict of {uri as string: mtime as int}
        """
        with SqlCursor(App().db) as sql:
            mtimes = {}
            result = sql.execute("SELECT DISTINCT uri, mtime\
                                  FROM tracks")
            for row in result:
                mtimes.update((row,))
            return mtimes

    def remove_album(self, album_id, commit=True):
        """
            Remove album
            @param album_id as int
        """
        with SqlCursor(App().db, commit) as sql:
            sql.execute("DELETE FROM tracks WHERE album_id=?", (album_id,))

    def del_non_persistent(self, commit=True):
        """
            Delete non persistent tracks
            @param commit as bool
        """
        with SqlCursor(App().db, commit) as sql:
            sql.execute("DELETE FROM tracks WHERE storage_type=?",
                        (StorageType.EPHEMERAL,))

    def del_old_for_storage_type(self, storage_type, offset=604800):
        """
            Delete album id tracks
            @param storage_type as StorageType
            @param offset as int
        """
        # Last week
        timestamp = time() - offset
        with SqlCursor(App().db, True) as sql:
            sql.execute("DELETE FROM tracks\
                         WHERE storage_type=? AND\
                         mtime < ?",
                        (storage_type, timestamp))

    def get_uris(self, uris_concerned=None):
        """
            Get all tracks uri
            @param uris_concerned as [uri as str]
            @return [str]
        """
        with SqlCursor(App().db) as sql:
            uris = []
            if uris_concerned:
                for uri in uris_concerned:
                    result = sql.execute("SELECT uri\
                                          FROM tracks\
                                          WHERE uri LIKE ? AND\
                                          storage_type & ?",
                                         (uri + "%", StorageType.COLLECTION))
                    uris += list(itertools.chain(*result))
            else:
                result = sql.execute("SELECT uri FROM tracks\
                                      WHERE  storage_type & ?",
                                     (StorageType.COLLECTION,))
                uris = list(itertools.chain(*result))
            return uris

    def get_number(self, track_id):
        """
            Get track position in album
            @param track_id as int
            @return position as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT tracknumber FROM tracks\
                                  WHERE rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_discnumber(self, track_id):
        """
            Get disc number for track id
            @param track_id as int
            @return discnumber as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT discnumber FROM tracks\
                                  WHERE rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_discname(self, track_id):
        """
            Get disc name for track id
            @param track_id as int
            @return discname as str
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT discname FROM tracks\
                                  WHERE rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_duration(self, track_id):
        """
            Get track duration for track id
            @param track_id as int
            @return duration as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT duration FROM tracks\
                                  WHERE rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def set_duration(self, track_id, duration):
        """
            Get track duration for track id
            @param track_id as int
            @param duration as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks\
                         SET duration=?\
                         WHERE rowid=?", (duration, track_id,))

    def set_mtime(self, track_id, mtime):
        """
            Set track_mtime
            @param track_id as int
            @param mtime as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks SET mtime=? WHERE rowid=?",
                        (mtime, track_id))

    def is_empty(self):
        """
            Return True if no tracks in db
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT COUNT(1) FROM tracks  LIMIT 1")
            v = result.fetchone()
            if v is not None:
                return v[0] == 0
            return True

    def get_for_artist(self, artist_id):
        """
            Get tracks for artist_id where artist_id isn't main artist
            @param artist_id as int
            @return list of [tracks id as int, track name as string]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT tracks.rowid\
                                 FROM tracks, track_artists, album_artists\
                                 WHERE album_artists.album_id=tracks.album_id\
                                 AND track_artists.artist_id=?\
                                 AND track_artists.track_id=tracks.rowid\
                                 AND NOT EXISTS (\
                                  SELECT artist_id\
                                  FROM album_artists\
                                  WHERE artist_id=track_artists.artist_id\
                                  AND album_id=tracks.album_id)",
                                 (artist_id,))
            return list(itertools.chain(*result))

    def get_rated(self, limit=100):
        """
            Return tracks with rate >= 4
            @param limit as int
            @return tracks as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE rate >= 4\
                                  ORDER BY popularity DESC LIMIT ?",
                                 (limit,))
            return list(itertools.chain(*result))

    def get_populars(self, limit=100):
        """
            Return populars tracks
            @param limit as int
            @return tracks as [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks\
                                  WHERE popularity!=0 AND mtime != 0\
                                  ORDER BY popularity DESC LIMIT ?",
                                 (limit,))
            return list(itertools.chain(*result))

    def get_higher_popularity(self):
        """
            Get higher available popularity
            @return int
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            result = sql.execute("SELECT popularity\
                                  FROM tracks WHERE storage_type & ?\
                                  ORDER BY POPULARITY DESC LIMIT 1",
                                 (storage_type,))
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
            storage_type = StorageType.COLLECTION | StorageType.SAVED
            result = sql.execute("SELECT AVG(popularity)\
                                  FROM (SELECT popularity\
                                        FROM tracks\
                                        WHERE storage_type & ?\
                                        ORDER BY POPULARITY DESC LIMIT 100)",
                                 (storage_type,))
            v = result.fetchone()
            if v and v[0] > 5:
                return v[0]
            return 5

    def set_more_popular(self, track_id):
        """
            Increment popularity field
            @param track_id as int
            @raise sqlite3.OperationalError on db update
        """
        with SqlCursor(App().db, True) as sql:
            result = sql.execute("SELECT popularity from tracks WHERE rowid=?",
                                 (track_id,))
            pop = result.fetchone()
            if pop:
                current = pop[0]
            else:
                current = 0
            current += 1
            sql.execute("UPDATE tracks set popularity=? WHERE rowid=?",
                        (current, track_id))

    def set_listened_at(self, track_id, time):
        """
            Set ltime for track
            @param track_id as int
            @param time as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks set ltime=? WHERE rowid=?",
                        (time, track_id))

    def get_never_listened_to(self):
        """
            Return random tracks never listened to
            @return tracks as [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            result = sql.execute("SELECT tracks.rowid\
                                  FROM tracks\
                                  WHERE ltime=0 AND storage_type & ?\
                                  ORDER BY random() LIMIT 100",
                                 (storage_type,))
            return list(itertools.chain(*result))

    def get_recently_listened_to(self):
        """
            Return tracks listened recently
            @return tracks as [int]
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            result = sql.execute("SELECT tracks.rowid\
                                  FROM tracks\
                                  WHERE ltime!=0 AND storage_type & ?\
                                  ORDER BY ltime DESC LIMIT 100",
                                 (storage_type,))
            return list(itertools.chain(*result))

    def get_randoms(self):
        """
            Return random tracks
            @return array of track ids as int
        """
        with SqlCursor(App().db) as sql:
            storage_type = get_default_storage_type()
            result = sql.execute("SELECT tracks.rowid\
                                  FROM tracks WHERE storage_type & ?\
                                  ORDER BY random() LIMIT 100",
                                 (storage_type,))
            tracks = list(itertools.chain(*result))
            return tracks

    def set_popularity(self, track_id, popularity):
        """
            Set popularity
            @param track_id as int
            @param popularity as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks set popularity=? WHERE rowid=?",
                        (popularity, track_id))

    def get_popularity(self, track_id):
        """
            Get popularity
            @param track_id  as int
            @return popularity as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT popularity FROM tracks WHERE\
                                 rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_loved(self, track_id):
        """
            Get track loved status
            @param track_id as int
            @return loved as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT loved FROM tracks WHERE\
                                 rowid=?", (track_id,))

            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_loved_track_ids(self):
        """
            Get loved track ids
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid FROM tracks WHERE loved=1")
            return list(itertools.chain(*result))

    def get_ltime(self, track_id):
        """
            Get listen time
            @param track_id  as int
            @return listen time as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT ltime FROM tracks WHERE\
                                 rowid=?", (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_mtime(self, track_id):
        """
            Get modification time
            @param track_id as int
            @return modification time as int
        """
        with SqlCursor(App().db) as sql:
            request = "SELECT mtime FROM tracks\
                       WHERE tracks.rowid=?"
            result = sql.execute(request, (track_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def set_loved(self, track_id, loved):
        """
            Set track loved
            @param track_id as int
            @param loved as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("UPDATE tracks SET loved=? WHERE rowid=?",
                        (loved, track_id))

    def count(self):
        """
            Count tracks
            @return int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT COUNT(1) FROM tracks\
                                  WHERE storage_type & ?",
                                 (StorageType.COLLECTION | StorageType.SAVED,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def clean(self, commit=True):
        """
            Clean database for track id
            @param commit as bool
        """
        with SqlCursor(App().db, commit) as sql:
            sql.execute("DELETE FROM track_artists\
                         WHERE track_artists.track_id NOT IN (\
                            SELECT tracks.rowid FROM tracks)")
            sql.execute("DELETE FROM track_genres\
                         WHERE track_genres.track_id NOT IN (\
                            SELECT tracks.rowid FROM tracks)")

    def search(self, searched, storage_type):
        """
            Search for tracks looking like searched
            @param searched as str
            @param storage_type as StorageType
            @return [int]
        """
        with SqlCursor(App().db) as sql:
            no_accents = noaccents(searched)
            items = []
            # From best filter to worst filter
            for filter in [(no_accents + "%", storage_type),
                           ("%" + no_accents, storage_type),
                           ("%" + no_accents + "%", storage_type)]:
                request = "SELECT tracks.rowid FROM tracks\
                           WHERE noaccents(name) LIKE ?\
                           AND tracks.storage_type & ? LIMIT 25"
                result = sql.execute(request, filter)
                items += list(itertools.chain(*result))
            for filter in [(Type.COMPILATIONS, no_accents + "%", storage_type),
                           (Type.COMPILATIONS, "%" + no_accents, storage_type),
                           (Type.COMPILATIONS, "%" + no_accents + "%",
                            storage_type)]:
                request = "SELECT DISTINCT tracks.rowid\
                       FROM track_artists, album_artists, tracks, artists\
                       WHERE tracks.album_id=album_artists.album_id AND\
                       album_artists.artist_id != ? AND\
                       track_artists.artist_id=artists.rowid AND\
                       track_artists.track_id=tracks.rowid AND\
                       noaccents(artists.name) LIKE ? AND\
                       tracks.storage_type & ? LIMIT 25"
                result = sql.execute(request, filter)
                items += list(itertools.chain(*result))
            return list(set(items))

    def search_track(self, artist, title):
        """
            Get track id for artist and title
            @param artist as string
            @param title as string
            @return track id as int
        """
        artist = noaccents(artist.lower())
        track_ids = self.get_ids_for_name(title)
        for track_id in track_ids:
            album_id = App().tracks.get_album_id(track_id)
            artist_ids = set(App().albums.get_artist_ids(album_id)) &\
                set(App().tracks.get_artist_ids(track_id))
            for artist_id in artist_ids:
                db_artist = noaccents(
                    App().artists.get_name(artist_id).lower())
                if artist.find(db_artist) != -1 or\
                        db_artist.find(artist) != -1:
                    return track_id
            artists = ", ".join(App().tracks.get_artists(track_id)).lower()
            if noaccents(artists) == artist:
                return track_id
        return None

    def remove(self, track_id):
        """
            Remove track
            @param track_id as int
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("DELETE FROM track_genres\
                         WHERE track_id=?", (track_id,))
            sql.execute("DELETE FROM track_artists\
                         WHERE track_id=?", (track_id,))
            sql.execute("DELETE FROM tracks\
                         WHERE rowid=?", (track_id,))
