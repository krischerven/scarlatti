# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2019 Jordi Romera <jordiromera@users.sourceforge.net>
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

from gi.repository import GLib, GObject, Gio

from gi.repository.Gio import FILE_ATTRIBUTE_STANDARD_NAME, \
                              FILE_ATTRIBUTE_STANDARD_TYPE, \
                              FILE_ATTRIBUTE_STANDARD_IS_HIDDEN,\
                              FILE_ATTRIBUTE_TIME_MODIFIED

from gettext import gettext as _
from threading import Thread
from time import time
import json

from lollypop.inotify import Inotify
from lollypop.define import App, ScanType, Type
from lollypop.sqlcursor import SqlCursor
from lollypop.tagreader import TagReader
from lollypop.logger import Logger
from lollypop.database_history import History
from lollypop.utils import is_audio, is_pls, get_mtime, profile, create_dir


SCAN_QUERY_INFO = "{},{},{},{}".format(FILE_ATTRIBUTE_STANDARD_NAME,
                                       FILE_ATTRIBUTE_STANDARD_TYPE,
                                       FILE_ATTRIBUTE_STANDARD_IS_HIDDEN,
                                       FILE_ATTRIBUTE_TIME_MODIFIED)


class CollectionScanner(GObject.GObject, TagReader):
    """
        Scan user music collection
    """
    __gsignals__ = {
        "scan-finished": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "artist-updated": (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "genre-updated": (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "album-updated": (GObject.SignalFlags.RUN_FIRST, None, (int, bool))
    }

    _WEB_COLLECTION = GLib.get_user_data_dir() + "/lollypop/web_collection"

    def __init__(self):
        """
            Init collection scanner
        """
        GObject.GObject.__init__(self)
        TagReader.__init__(self)

        self.__thread = None
        self.__history = History()
        self.__disable_compilations = True
        if App().settings.get_value("auto-update"):
            self.__inotify = Inotify()
        else:
            self.__inotify = None
        App().albums.update_max_count()
        create_dir(self._WEB_COLLECTION)

    def update(self, scan_type, uris=[]):
        """
            Update database
            @param scan_type as ScanType
            @param uris as [str]
        """
        App().lookup_action("update_db").set_enabled(False)
        # Stop previous scan
        if self.is_locked() and scan_type != ScanType.EPHEMERAL:
            self.stop()
            GLib.timeout_add(250, self.update, scan_type, uris)
        else:
            self.__disable_compilations = not App().settings.get_value(
                "show-compilations")

            if scan_type == ScanType.FULL:
                uris = App().settings.get_music_uris()
            if not uris:
                return
            # Register to progressbar
            if scan_type != ScanType.EPHEMERAL:
                App().window.container.progress.add(self)
                App().window.container.progress.set_fraction(0, self)
            # Launch scan in a separate thread
            self.__thread = Thread(target=self.__scan, args=(scan_type, uris))
            self.__thread.daemon = True
            self.__thread.start()

    def update_album(self, album_id, album_artist_ids,
                     genre_ids, year, timestamp):
        """
            Update album artists based on album-artist and artist tags
            This code auto handle compilations: empty "album artist" with
            different artists
            @param album_id as int
            @param album_artist_ids as [int]
            @param genre_ids as [int]
            @param year as int
            @param timestamp as int
            @commit needed
        """
        if album_artist_ids:
            # Update UI based on previous artist calculation
            mtime = App().albums.get_mtime(album_id)
            if mtime != 0:
                for artist_id in album_artist_ids:
                    GLib.idle_add(self.emit, "artist-updated", artist_id, True)
            App().albums.set_artist_ids(album_id, album_artist_ids)
        # Set artist ids based on content
        else:
            new_album_artist_ids = App().albums.calculate_artist_ids(album_id)
            App().albums.set_artist_ids(album_id, new_album_artist_ids)
        # Update album genres
        for genre_id in genre_ids:
            App().albums.add_genre(album_id, genre_id)
        # Update year based on tracks
        year = App().tracks.get_year_for_album(album_id)
        App().albums.set_year(album_id, year)
        timestamp = App().tracks.get_timestamp_for_album(album_id)
        App().albums.set_timestamp(album_id, timestamp)

    def save_track(self, genres, artists, a_sortnames, mb_artist_id,
                   album_artists, aa_sortnames, mb_album_artist_id,
                   album_name, mb_album_id, uri, album_loved, album_pop,
                   album_rate, album_synced, album_mtime, title, duration,
                   tracknumber, discnumber, discname, year, timestamp,
                   track_mtime, track_pop, track_rate, track_loved,
                   track_ltime, mb_track_id, bpm):
        """
            Add track to DB
            @param genres as str/None
            @param artists as str
            @param a_sortnames as str
            @param mb_artist_id as str
            @param album_artists as str
            @param aa_sortnames as str
            @param mb_album_artist_id as str
            @param album_name as str
            @param mb_album_id as str
            @param uri as str
            @param album_loved as int
            @param album_pop as int
            @param album_rate as int
            @param album_synced as int
            @param album_mtime as int
            @param title as str
            @param duration as int
            @param tracknumber as int
            @param discnumber as int
            @param discname as str
            @param year as int
            @param timestamp as int
            @param track_mtime as int
            @param track_pop as int
            @param track_rate as int
            @param track_loved as int
            @param track_ltime as int
            @param mb_track_id as str
            @param bpm as int
        """
        Logger.debug(
            "CollectionScanner::save_track(): Add artists %s" % artists)
        artist_ids = self.add_artists(artists, a_sortnames, mb_artist_id)

        Logger.debug("CollectionScanner::save_track(): "
                     "Add album artists %s" % album_artists)
        album_artist_ids = self.add_artists(album_artists, aa_sortnames,
                                            mb_album_artist_id)

        # User does not want compilations
        if self.__disable_compilations and not album_artist_ids:
            album_artist_ids = artist_ids

        missing_artist_ids = list(set(album_artist_ids) - set(artist_ids))
        # https://github.com/gnumdk/lollypop/issues/507#issuecomment-200526942
        # Special case for broken tags
        # Can't do more because don't want to break split album behaviour
        if len(missing_artist_ids) == len(album_artist_ids):
            artist_ids += missing_artist_ids

        Logger.debug("CollectionScanner::save_track(): Add album: "
                     "%s, %s" % (album_name, album_artist_ids))
        (album_added, album_id) = self.add_album(album_name, mb_album_id,
                                                 album_artist_ids,
                                                 uri, album_loved, album_pop,
                                                 album_rate, album_synced,
                                                 album_mtime)
        if genres is None:
            genre_ids = [Type.WEB]
        else:
            genre_ids = self.add_genres(genres)

        # Add track to db
        Logger.debug("CollectionScanner::save_track(): Add track")
        track_id = App().tracks.add(title, uri, duration,
                                    tracknumber, discnumber, discname,
                                    album_id, year, timestamp, track_pop,
                                    track_rate, track_loved, track_ltime,
                                    track_mtime, mb_track_id, bpm)
        Logger.debug("CollectionScanner::save_track(): Update track")
        self.update_track(track_id, artist_ids, genre_ids)
        Logger.debug("CollectionScanner::save_track(): Update album")
        SqlCursor.commit(App().db)
        self.update_album(album_id, album_artist_ids,
                          genre_ids, year, timestamp)
        SqlCursor.commit(App().db)
        for genre_id in genre_ids:
            # Be sure to not send Type.WEB
            if genre_id >= 0:
                GLib.idle_add(self.emit, "genre-updated", genre_id, True)
        if album_added:
            GLib.idle_add(self.emit, "album-updated", album_id, True)
        return (track_id, album_id)

    def update_track(self, track_id, artist_ids, genre_ids):
        """
            Set track artists/genres
            @param track_id as int
            @param artist_ids as [int]
            @param genre_ids as [int]
            @commit needed
        """
        # Set artists/genres for track
        for artist_id in artist_ids:
            App().tracks.add_artist(track_id, artist_id)
        for genre_id in genre_ids:
            App().tracks.add_genre(track_id, genre_id)

    def del_from_db(self, uri, backup, notify=True):
        """
            Delete track from db
            @param uri as str
            @param backup as bool
            @param notify as bool => send signal about cleanup
            @return (popularity, ltime, mtime,
                     loved album, album_popularity)
        """
        try:
            track_id = App().tracks.get_id_by_uri(uri)
            duration = App().tracks.get_duration(track_id)
            album_id = App().tracks.get_album_id(track_id)
            genre_ids = App().tracks.get_genre_ids(track_id)
            album_artist_ids = App().albums.get_artist_ids(album_id)
            artist_ids = App().tracks.get_artist_ids(track_id)
            track_pop = App().tracks.get_popularity(track_id)
            track_rate = App().tracks.get_rate(track_id)
            track_ltime = App().tracks.get_ltime(track_id)
            album_mtime = App().tracks.get_mtime(track_id)
            track_loved = App().tracks.get_loved(track_id)
            album_pop = App().albums.get_popularity(album_id)
            album_rate = App().albums.get_rate(album_id)
            album_loved = App().albums.get_loved(album_id)
            album_synced = App().albums.get_synced(album_id)
            # Force genre for album
            App().albums.set_genre_ids(album_id, genre_ids)
            if backup:
                f = Gio.File.new_for_uri(uri)
                name = f.get_basename()
                self.__history.add(name, duration, track_pop, track_rate,
                                   track_ltime, album_mtime, track_loved,
                                   album_loved, album_pop, album_rate,
                                   album_synced)
            App().tracks.remove(track_id)
            App().albums.clean()
            App().genres.clean()
            App().artists.clean()
            if notify:
                if App().albums.get_name(album_id) is None:
                    GLib.idle_add(self.emit, "album-updated",
                                  album_id, False)
                for artist_id in album_artist_ids + artist_ids:
                    GLib.idle_add(self.emit, "artist-updated",
                                  artist_id, False)
                for genre_id in genre_ids:
                    GLib.idle_add(self.emit, "genre-updated",
                                  genre_id, False)
            return (track_pop, track_rate, track_ltime, album_mtime,
                    track_loved, album_loved, album_pop, album_rate)
        except Exception as e:
            Logger.error("CollectionScanner::del_from_db: %s" % e)

    def is_locked(self):
        """
            Return True if db locked
        """
        return self.__thread is not None and self.__thread.isAlive()

    def stop(self):
        """
            Stop scan
        """
        self.__thread = None

    @property
    def inotify(self):
        """
            Get Inotify object
            @return Inotify
        """
        return self.__inotify

#######################
# PRIVATE             #
#######################
    def __update_progress(self, current, total):
        """
            Update progress bar status
            @param scanned items as int, total items as int
        """
        GLib.idle_add(App().window.container.progress.set_fraction,
                      current / total,
                      self)

    def __finish(self, modifications):
        """
            Notify from main thread when scan finished
            @param modifications as bool
        """
        App().lookup_action("update_db").set_enabled(True)
        App().window.container.progress.set_fraction(1.0, self)
        self.stop()
        self.emit("scan-finished", modifications)
        # Update max count value
        App().albums.update_max_count()

    def __add_monitor(self, dirs):
        """
            Monitor any change in a list of directory
            @param dirs as str or list of directory to be monitored
        """
        if self.__inotify is None:
            return
        # Add monitors on dirs
        for d in dirs:
            # Handle a stop request
            if self.__thread is None:
                break
            if d.startswith("file://"):
                self.__inotify.add_monitor(d)

    def __import_web_tracks(self):
        """
            Import locally saved web tracks
        """
        try:
            # Directly add files, walk through directories
            f = Gio.File.new_for_path(self._WEB_COLLECTION)
            infos = f.enumerate_children(SCAN_QUERY_INFO,
                                         Gio.FileQueryInfoFlags.NONE,
                                         None)
            for info in infos:
                f = infos.get_child(info)
                if info.get_is_hidden():
                    continue
                elif info.get_file_type() == Gio.FileType.DIRECTORY:
                    pass
                else:
                    (status, content, tag) = f.load_contents()
                    data = json.loads(content)
                    self.save_track(
                       None, ";".join(data["artists"]), "", "",
                       ";".join(data["album_artists"]),
                       "", "", data["album_name"], "", data["uri"],
                       data["album_loved"], data["album_popularity"],
                       data["album_rate"], 0, -1, data["title"],
                       data["duration"], data["tracknumber"],
                       data["discnumber"], data["discname"], data["year"],
                       data["timestamp"], -1, data["track_popularity"],
                       data["track_rate"], data["track_loved"], 0, "", 0)
            infos.close(None)
        except Exception as e:
            Logger.error("CollectionScanner::__import_web_tracks(): %s", e)

    @profile
    def __get_objects_for_uris(self, scan_type, uris):
        """
            Get all tracks and dirs in uris
            @param scan_type as ScanType
            @param uris as string
            @return (tracks [mtimes: int, uri: str], dirs as [uri: str])
        """
        files = []
        dirs = []
        walk_uris = []
        # Check collection exists
        for uri in uris:
            f = Gio.File.new_for_uri(uri)
            if f.query_exists():
                walk_uris.append(uri)
            else:
                return (None, None)

        while walk_uris:
            uri = walk_uris.pop(0)
            try:
                # Directly add files, walk through directories
                f = Gio.File.new_for_uri(uri)
                info = f.query_info(SCAN_QUERY_INFO,
                                    Gio.FileQueryInfoFlags.NONE,
                                    None)
                if info.get_file_type() == Gio.FileType.DIRECTORY:
                    dirs.append(uri)
                    infos = f.enumerate_children(SCAN_QUERY_INFO,
                                                 Gio.FileQueryInfoFlags.NONE,
                                                 None)
                    for info in infos:
                        f = infos.get_child(info)
                        child_uri = f.get_uri()
                        if info.get_is_hidden():
                            continue
                        elif info.get_file_type() == Gio.FileType.DIRECTORY:
                            dirs.append(child_uri)
                            walk_uris.append(child_uri)
                        else:
                            mtime = get_mtime(info)
                            files.append((mtime, child_uri))
                    infos.close(None)
                # Only happens if files passed as args
                else:
                    mtime = get_mtime(info)
                    files.append((mtime, uri))
            except Exception as e:
                Logger.error("CollectionScanner::__get_objects_for_uris(): %s"
                             % e)
        files.sort(reverse=True)
        return (files, dirs)

    @profile
    def __scan(self, scan_type, uris):
        """
            Scan music collection for music files
            @param scan_type as ScanType
            @param uris as [str]
            @thread safe
        """
        if not App().tracks.get_mtimes():
            self.__import_web_tracks()

        (files, dirs) = self.__get_objects_for_uris(scan_type, uris)

        if files is None:
            if App().notify is not None:
                App().notify.send(_("Scan disabled, missing collection"))
            return

        if scan_type == ScanType.NEW_FILES:
            db_uris = App().tracks.get_uris(uris)
        else:
            db_uris = App().tracks.get_uris()
        new_tracks = self.__scan_files(files, db_uris, scan_type)

        if scan_type != ScanType.EPHEMERAL:
            self.__add_monitor(dirs)
            GLib.idle_add(self.__finish, new_tracks)

        if scan_type == ScanType.EPHEMERAL:
            App().player.play_uris(new_tracks)

    def __scan_to_handle(self, uri):
        """
            Check if file has to be handle by scanner
            @param f as Gio.File
            @return bool
        """
        try:
            f = Gio.File.new_for_uri(uri)
            # Scan file
            if App().settings.get_value("import-playlists") and is_pls(f):
                # Handle playlist
                App().playlists.import_tracks(f)
            elif is_audio(f):
                return True
            else:
                Logger.debug("Not detected as a music file: %s" % f.get_uri())
        except Exception as e:
            Logger.error("CollectionScanner::__scan_to_handle(): %s" % e)
        return False

    @profile
    def __scan_files(self, files, db_uris, scan_type):
        """
            Scan music collection for new audio files
            @param files as [str]
            @param db_uris as [str]
            @param scan_type as ScanType
            @return new track uris as [str]
            @thread safe
        """
        SqlCursor.add(App().db)
        i = 0
        # New tracks present in collection
        new_tracks = []
        # Get mtime of all tracks to detect which has to be updated
        db_mtimes = App().tracks.get_mtimes()
        count = len(files) + 1
        try:
            # Scan new files
            for (mtime, uri) in files:
                # Handle a stop request
                if self.__thread is None and scan_type != ScanType.EPHEMERAL:
                    raise Exception("Scan add cancelled")
                try:
                    if not self.__scan_to_handle(uri):
                        continue
                    if mtime > db_mtimes.get(uri, 0):
                        # If not saved, use 0 as mtime, easy delete on quit
                        if scan_type == ScanType.EPHEMERAL:
                            mtime = 0
                        # Do not use mtime if not intial scan
                        elif db_mtimes:
                            mtime = int(time())
                        Logger.debug("Adding file: %s" % uri)
                        self.__add2db(uri, mtime)
                        SqlCursor.allow_thread_execution(App().db)
                        new_tracks.append(uri)
                except Exception as e:
                    Logger.error(
                               "CollectionScanner:: __scan_add_files: % s" % e)
                i += 1
                self.__update_progress(i, count)
            if scan_type != ScanType.EPHEMERAL and self.__thread is not None:
                # We need to check files are always in collections
                if scan_type == ScanType.FULL:
                    collections = App().settings.get_music_uris()
                else:
                    collections = None
                for uri in db_uris:
                    # Handle a stop request
                    if self.__thread is None:
                        raise Exception("Scan del cancelled")
                    in_collection = True
                    if collections is not None:
                        in_collection = False
                        for collection in collections:
                            if collection in uri:
                                in_collection = True
                                break
                    f = Gio.File.new_for_uri(uri)
                    if not in_collection or not f.query_exists():
                        self.del_from_db(uri, True)
                        SqlCursor.allow_thread_execution(App().db)
        except Exception as e:
            Logger.warning("CollectionScanner:: __scan_files: % s" % e)
        SqlCursor.commit(App().db)
        SqlCursor.remove(App().db)
        return new_tracks

    def __add2db(self, uri, track_mtime):
        """
            Add new file(or update one) to db with information
            @param uri as string
            @param track_mtime as int
            @return track id as int
            @warning, be sure SqlCursor is available for App().db
        """
        f = Gio.File.new_for_uri(uri)
        Logger.debug("CollectionScanner::add2db(): Read tags")
        info = self.get_info(uri)
        tags = info.get_tags()
        name = f.get_basename()
        title = self.get_title(tags, name)
        version = self.get_version(tags)
        artists = self.get_artists(tags)
        composers = self.get_composers(tags)
        performers = self.get_performers(tags)
        remixers = self.get_remixers(tags)
        if remixers != "":
            artists += ";%s" % remixers
        a_sortnames = self.get_artist_sortnames(tags)
        aa_sortnames = self.get_album_artist_sortnames(tags)
        album_artists = self.get_album_artists(tags)
        album_name = self.get_album_name(tags)
        album_synced = 0
        mb_album_id = self.get_mb_album_id(tags)
        mb_track_id = self.get_mb_track_id(tags)
        mb_artist_id = self.get_mb_artist_id(tags)
        mb_album_artist_id = self.get_mb_album_artist_id(tags)
        genres = self.get_genres(tags)
        discnumber = self.get_discnumber(tags)
        discname = self.get_discname(tags)
        tracknumber = self.get_tracknumber(tags, name)
        track_popm = self.get_popm(tags)
        bpm = self.get_bpm(tags)
        (year, timestamp) = self.get_original_year(tags)
        if year is None:
            (year, timestamp) = self.get_year(tags)
        duration = int(info.get_duration() / 1000000000)

        if version != "":
            title += " (%s)" % version

        # If no artists tag, use album artist
        if artists == "":
            artists = album_artists
        # if artists is always null, no album artists too,
        # use composer/performer
        if artists == "":
            artists = performers
            album_artists = composers
            if artists == "":
                artists = album_artists
            if artists == "":
                artists = _("Unknown")

        Logger.debug("CollectionScanner::add2db(): Restore stats")
        # Restore stats
        track_id = App().tracks.get_id_by_uri(uri)
        if track_id is None:
            basename = f.get_basename()
            track_id = App().tracks.get_id_by_basename_duration(basename,
                                                                duration)
        if track_id is None:
            (track_pop, track_rate, track_ltime,
             album_mtime, track_loved, album_loved,
             album_pop, album_rate, album_synced) = self.__history.get(
                name, duration)
        # Delete track and restore from it
        else:
            (track_pop, track_rate, track_ltime,
             album_mtime, track_loved, album_loved,
             album_pop, album_rate) = self.del_from_db(uri, False)
        # Prefer popm to internal rate
        if track_popm != 0:
            track_rate = track_popm
        # If nothing in stats, use track mtime
        if album_mtime == 0:
            album_mtime = track_mtime

        (track_id, album_id) = self.save_track(
                   genres, artists, a_sortnames, mb_artist_id,
                   album_artists, aa_sortnames, mb_album_artist_id,
                   album_name, mb_album_id, uri, album_loved, album_pop,
                   album_rate, album_synced, album_mtime, title, duration,
                   tracknumber, discnumber, discname, year, timestamp,
                   track_mtime, track_pop, track_rate, track_loved,
                   track_ltime, mb_track_id, bpm)
        return track_id
