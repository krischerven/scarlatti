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

from gi.repository import GLib, Gio

import sqlite3
from threading import Lock
import itertools

from lollypop.define import App, StorageType
from lollypop.database_upgrade import DatabaseAlbumsUpgrade
from lollypop.sqlcursor import SqlCursor
from lollypop.logger import Logger
from lollypop.localized import LocalizedCollation
from lollypop.utils import noaccents


class MyLock:
    """
        Lock with count
    """
    def __init__(self):
        self.__lock = Lock()
        self.__count = 0

    def acquire(self):
        self.__count += 1
        self.__lock.acquire()

    def release(self):
        self.__count -= 1
        self.__lock.release()

    @property
    def count(self):
        return self.__count


class Database:
    """
        Base database object
    """
    __LOCAL_PATH = GLib.get_user_data_dir() + "/lollypop"
    DB_PATH = "%s/lollypop.db" % __LOCAL_PATH

    # SQLite documentation:
    # In SQLite, a column with type INTEGER PRIMARY KEY
    # is an alias for the ROWID.
    # Here, we define an id INT PRIMARY KEY but never feed it,
    # this make VACUUM not destroy rowids...
    __create_albums = """CREATE TABLE albums (id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL,
                                              mb_album_id TEXT,
                                              no_album_artist BOOLEAN NOT NULL,
                                              year INT,
                                              timestamp INT,
                                              uri TEXT NOT NULL,
                                              popularity INT NOT NULL,
                                              rate INT NOT NULL,
                                              loved INT NOT NULL,
                                              mtime INT NOT NULL,
                                              storage_type INT NOT NULL,
                                              synced INT NOT NULL)"""
    __create_artists = """CREATE TABLE artists (id INTEGER PRIMARY KEY,
                                               name TEXT NOT NULL,
                                               sortname TEXT NOT NULL,
                                               mb_artist_id TEXT)"""
    __create_genres = """CREATE TABLE genres (id INTEGER PRIMARY KEY,
                                            name TEXT NOT NULL)"""
    __create_album_artists = """CREATE TABLE album_artists (
                                                album_id INT NOT NULL,
                                                artist_id INT NOT NULL)"""
    __create_album_genres = """CREATE TABLE album_genres (
                                                album_id INT NOT NULL,
                                                genre_id INT NOT NULL)"""
    __create_tracks = """CREATE TABLE tracks (id INTEGER PRIMARY KEY,
                                              name TEXT NOT NULL,
                                              uri TEXT NOT NULL,
                                              duration INT,
                                              tracknumber INT,
                                              discnumber INT,
                                              discname TEXT,
                                              album_id INT NOT NULL,
                                              year INT,
                                              timestamp INT,
                                              popularity INT NOT NULL,
                                              loved INT NOT NULL DEFAULT 0,
                                              rate INT NOT NULL,
                                              ltime INT NOT NULL,
                                              mtime INT NOT NULL,
                                              storage_type INT NOT NULL,
                                              mb_track_id TEXT,
                                              bpm DOUBLE
                                              )"""
    __create_track_artists = """CREATE TABLE track_artists (
                                                track_id INT NOT NULL,
                                                artist_id INT NOT NULL)"""
    __create_track_genres = """CREATE TABLE track_genres (
                                                track_id INT NOT NULL,
                                                genre_id INT NOT NULL)"""
    __create_album_artists_idx = """CREATE index idx_aa ON album_artists(
                                                album_id)"""
    __create_track_artists_idx = """CREATE index idx_ta ON track_artists(
                                                track_id)"""
    __create_album_genres_idx = """CREATE index idx_ag ON album_genres(
                                                album_id)"""
    __create_track_genres_idx = """CREATE index idx_tg ON track_genres(
                                                track_id)"""

    def __init__(self):
        """
            Create database tables or manage update if needed
        """
        self.thread_lock = MyLock()
        f = Gio.File.new_for_path(self.DB_PATH)
        upgrade = DatabaseAlbumsUpgrade()
        if not f.query_exists():
            try:
                d = Gio.File.new_for_path(self.__LOCAL_PATH)
                if not d.query_exists():
                    d.make_directory_with_parents()
                # Create db schema
                with SqlCursor(self, True) as sql:
                    sql.execute(self.__create_albums)
                    sql.execute(self.__create_artists)
                    sql.execute(self.__create_genres)
                    sql.execute(self.__create_album_genres)
                    sql.execute(self.__create_album_artists)
                    sql.execute(self.__create_tracks)
                    sql.execute(self.__create_track_artists)
                    sql.execute(self.__create_track_genres)
                    sql.execute(self.__create_album_artists_idx)
                    sql.execute(self.__create_track_artists_idx)
                    sql.execute(self.__create_album_genres_idx)
                    sql.execute(self.__create_track_genres_idx)
                    sql.execute("PRAGMA user_version=%s" % upgrade.version)
            except Exception as e:
                Logger.error("Database::__init__(): %s" % e)
        else:
            upgrade.upgrade(self)

    def execute(self, request):
        """
            Execute SQL request (only smart one)
            @param request as str
            @return list
        """
        try:
            with SqlCursor(App().db) as sql:
                result = sql.execute(request)
                # Special case for OR request
                if request.find("ORDER BY random()") == -1 and\
                        request.find("UNION") != -1:
                    ids = []
                    for (id, other) in list(result):
                        ids.append(id)
                    return ids
                else:
                    return list(itertools.chain(*result))
        except Exception as e:
            Logger.error("Database::execute(): %s -> %s", e, request)
        return []

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            c = sqlite3.connect(self.DB_PATH, 600.0)
            c.create_collation("LOCALIZED", LocalizedCollation())
            c.create_function("noaccents", 1, noaccents)
            return c
        except:
            exit(-1)

    def drop_db(self):
        """
            Drop database
        """
        try:
            f = Gio.File.new_for_path(self.DB_PATH)
            f.trash()
        except Exception as e:
            Logger.error("Database::drop_db():", e)

    def exists_in_db(self, album, artists, track):
        """
            Search if item exists in db
            @param track as str
            @param album as str
            @param artists as [str]
            @return object
        """
        artist_ids = []
        for artist in artists:
            artist_id = App().artists.get_id(artist)
            artist_ids.append(artist_id)
        album_id = App().albums.get_id_by_name_artists(album, artist_ids)
        if album_id is None:
            return None
        elif App().albums.get_storage_type(album_id) & StorageType.COLLECTION\
                or track is None:
            return album_id
        else:
            track_id = App().tracks.get_id_by(track,
                                              album_id,
                                              artist_ids)
            return track_id

#######################
# PRIVATE             #
#######################
