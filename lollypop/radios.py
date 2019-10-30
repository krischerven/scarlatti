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

from gi.repository import GObject, Gio, GLib

import sqlite3
import itertools
from threading import Lock

from lollypop.sqlcursor import SqlCursor
from lollypop.logger import Logger
from lollypop.utils import emit_signal


class Radios(GObject.GObject):
    """
        Playlists manager
    """
    __LOCAL_PATH = GLib.get_user_data_dir() + "/lollypop"
    DB_PATH = "%s/radios.db" % __LOCAL_PATH

    create_radios = """CREATE TABLE radios (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            url TEXT NOT NULL,
                            rate INT NOT NULL DEFAULT -1,
                            popularity INT NOT NULL)"""
    __gsignals__ = {
        # Add, rename, delete
        "radio-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self):
        """
            Init playlists manager
        """
        GObject.GObject.__init__(self)
        self.thread_lock = Lock()
        # Create db schema
        try:
            f = Gio.File.new_for_path(self.DB_PATH)
            if not f.query_exists():
                with SqlCursor(self, True) as sql:
                    sql.execute(self.create_radios)
        except Exception as e:
            Logger.error("Radios::__init__(self): %s", e)

    def add(self, name, uri):
        """
            Add a radio, update url if radio already exists in db
            @param name as str
            @param uri as str
            @return radio id as int
        """
        lastrowid = 0
        with SqlCursor(self, True) as sql:
            result = sql.execute("INSERT INTO radios (name, url, popularity)\
                                  VALUES (?, ?, ?)",
                                 (name, uri, 0))
            lastrowid = result.lastrowid
        emit_signal(self, "radio-changed", lastrowid)
        return lastrowid

    def exists(self, radio_id):
        """
            Return True if radio exists
            @param radio_id as int
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM radios\
                                  WHERE rowid=?",
                                 (radio_id,))
            v = result.fetchone()
            return v is not None

    def rename(self, radio_id, name):
        """
            Rename playlist
            @param radio_id as int
            @param name as str
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE radios\
                        SET name=?\
                        WHERE rowid=?",
                        (name, radio_id))
            emit_signal(self, "radio-changed", radio_id)

    def remove(self, radio_id):
        """
            Remvoe radio with radio id
            @param radio_id as int
        """
        with SqlCursor(self, True) as sql:
            sql.execute("DELETE FROM radios\
                        WHERE rowid=?",
                        (radio_id,))
        emit_signal(self, "radio-changed", radio_id)

    def get(self):
        """
            Return availables radios
            @return array of (name, url) as[(str, str)]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT name, url\
                                  FROM radios\
                                  ORDER BY rate DESC,\
                                  popularity DESC, name")
            return list(result)

    def get_ids(self):
        """
            Return availables radios
            @return [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM radios\
                                  ORDER BY rate DESC,\
                                  popularity DESC, name")
            return list(itertools.chain(*result))

    def get_name(self, radio_id):
        """
            Get radio name for id
            @param radio_id as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT name\
                                  FROM radios\
                                  WHERE rowid=?", (radio_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_uri(self, radio_id):
        """
            Get URI for id
            @param radio_id as int
            @return uri as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT url\
                                  FROM radios\
                                  WHERE rowid=?", (radio_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def set_more_popular(self, radio_id):
        """
            Set radio more popular
            @param radio_id as int
        """
        with SqlCursor(self, True) as sql:
            result = sql.execute("SELECT popularity from radios WHERE rowid=?",
                                 (radio_id,))
            pop = result.fetchone()
            if pop:
                current = pop[0]
            else:
                current = 0
            current += 1
            sql.execute("UPDATE radios set popularity=? WHERE rowid=?",
                        (current, radio_id))

    def get_higher_popularity(self):
        """
            Get higher available popularity
            @return int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT popularity\
                                  FROM radios\
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
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT AVG(popularity)\
                                  FROM (SELECT popularity\
                                        FROM radios\
                                        ORDER BY POPULARITY DESC LIMIT 100)")
            v = result.fetchone()
            if v and v[0] is not None and v[0] > 5:
                return v[0]
            return 5

    def set_popularity(self, radio_id, popularity):
        """
            Set popularity
            @param radio_id as int
            @param popularity as int
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE radios SET popularity=? WHERE rowid=?",
                        (popularity, radio_id))

    def set_rate(self, radio_id, rate):
        """
            Set rate
            @param radio_id as int
            @param rate as int
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE radios SET rate=? WHERE rowid=?",
                        (rate, radio_id))

    def set_uri(self, radio_id, uri):
        """
            Set uri
            @param radio_id as int
            @param uri as str
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE radios SET url=? WHERE rowid=?",
                        (uri, radio_id))

    def get_id(self, name):
        """
            Get radio id by name
            @param name as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT id FROM radios WHERE name=?", (name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_popularity(self, radio_id):
        """
            Get popularity
            @param radio_id as int
            @return popularity as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT popularity FROM radios WHERE rowid=?",
                                 (radio_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_rate(self, radio_id):
        """
            Get radio rate
            @param radio_id as int
            @return rate as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rate FROM radios WHERE rowid=?",
                                 (radio_id,))
            v = result.fetchone()
            if v:
                return v[0]
            return 0

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            return sqlite3.connect(self.DB_PATH, 600.0)
        except:
            exit(-1)

#######################
# PRIVATE             #
#######################
    def __on_entry_parsed(self, parser, uri, metadata, name):
        """
            Import entry
            @param parser as TotemPlParser.Parser
            @param radio uri as str
            @param metadata as GLib.HastTable
            @param name as str
        """
        self.add(name, uri)
