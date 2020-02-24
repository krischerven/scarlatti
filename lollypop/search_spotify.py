# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib, Soup, GObject, Gio

import json
from base64 import b64encode
from time import time, sleep
from random import choice, shuffle
from locale import getdefaultlocale

from lollypop.logger import Logger
from lollypop.utils import cancellable_sleep, get_network_available
from lollypop.utils import emit_signal, get_default_storage_type
from lollypop.objects_album import Album
from lollypop.sqlcursor import SqlCursor
from lollypop.helper_task import TaskHelper
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET, App, StorageType


class SpotifySearch(GObject.Object):
    """
        Search for Spotify
    """
    __MIN_ITEMS_PER_STORAGE_TYPE = 20
    __MAX_ITEMS_PER_STORAGE_TYPE = 50
    __gsignals__ = {
        "match-album": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-track": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "search-finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init object
        """
        GObject.Object.__init__(self)
        self.__token_expires = 0
        self.__token = None
        self.__loading_token = False
        self.__is_running = False
        self.__cancellable = Gio.Cancellable()

    def get_token(self, cancellable):
        """
            Get a new auth token
            @param cancellable as Gio.Cancellable
        """
        try:
            def on_response(uri, status, data):
                try:
                    decode = json.loads(data.decode("utf-8"))
                    self.__token_expires = int(time()) +\
                        int(decode["expires_in"])
                    self.__token = decode["access_token"]
                except Exception as e:
                    Logger.error("SpotifySearch::get_token(): %s", e)
            token_uri = "https://accounts.spotify.com/api/token"
            credentials = "%s:%s" % (SPOTIFY_CLIENT_ID, SPOTIFY_SECRET)
            encoded = b64encode(credentials.encode("utf-8"))
            credentials = encoded.decode("utf-8")
            data = {"grant_type": "client_credentials"}
            msg = Soup.form_request_new_from_hash("POST", token_uri, data)
            msg.request_headers.append("Authorization",
                                       "Basic %s" % credentials)
            App().task_helper.send_message(msg, cancellable, on_response)
        except Exception as e:
            Logger.error("SpotifySearch::get_token(): %s", e)

    def wait_for_token(self, cancellable):
        """
            True if should wait for token
            @param cancellable as Gio.Cancellable
            @return bool
        """
        def on_token(token):
            self.__loading_token = False
        # Remove 60 seconds to be sure
        wait = int(time()) + 60 > self.__token_expires or\
            self.__token is None
        if wait and not self.__loading_token:
            self.__loading_token = True
            App().task_helper.run(self.get_token, cancellable,
                                  callback=(on_token,))
        return wait

    def populate_db(self):
        """
            Populate DB in a background task
        """
        monitor = Gio.NetworkMonitor.get_default()
        if not monitor.get_network_metered() and\
                get_network_available("SPOTIFY"):
            App().task_helper.run(self.__populate_db)
        return True

    def get_artist_id(self, artist_name, cancellable):
        """
            Get artist id
            @param artist_name as str
            @param cancellable as Gio.Cancellable
        """
        try:
            while self.wait_for_token(cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            artist_name = GLib.uri_escape_string(
                artist_name, None, True).replace(" ", "+")
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?q=%s&type=artist" %\
                artist_name
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    artist_id = item["id"]
                    return artist_id
        except Exception as e:
            Logger.error("SpotifySearch::get_artist_id(): %s", e)
        return None

    def search_similar_albums(self, cancellable):
        """
            Add similar albums to DB
            @param cancellable as Gio.Cancellable
        """
        try:
            while self.wait_for_token(cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            storage_type = get_default_storage_type()
            artist_ids = App().artists.get_randoms(
                self.__MAX_ITEMS_PER_STORAGE_TYPE, storage_type)
            similar_ids = []
            # Get similars spotify ids
            for (artist_id, name, sortname) in artist_ids:
                cancellable_sleep(2, cancellable)
                spotify_id = self.get_artist_id(name, cancellable)
                if spotify_id is None:
                    continue
                similar_artists = self.get_similar_artists(spotify_id,
                                                           cancellable)
                for (similar_id, name, cover_uri) in similar_artists:
                    similar_ids.append(similar_id)
            # Add albums
            shuffle(similar_ids)
            for similar_id in similar_ids[:self.__MAX_ITEMS_PER_STORAGE_TYPE]:
                cancellable_sleep(2, cancellable)
                albums_payload = self.__get_artist_albums_payload(similar_id,
                                                                  cancellable)
                if albums_payload:
                    self.__create_albums_from_albums_payload(
                                           [choice(albums_payload)],
                                           StorageType.SPOTIFY_SIMILARS,
                                           True,
                                           cancellable)
        except Exception as e:
            Logger.warning("SpotifySearch::search_similar_albums(): %s", e)

    def search_new_releases(self, cancellable):
        """
            Get new released albums from spotify
            @param cancellable as Gio.Cancellable
        """
        locale = getdefaultlocale()[0][0:2]
        try:
            while self.wait_for_token(cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/browse/new-releases"
            uri += "?country=%s" % locale
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                self.__create_albums_from_albums_payload(
                                             decode["albums"]["items"],
                                             StorageType.SPOTIFY_NEW_RELEASES,
                                             True,
                                             cancellable)
        except Exception as e:
            Logger.warning("SpotifySearch::search_new_releases(): %s", e)

    def get_similar_artists(self, artist_id, cancellable):
        """
           Get similar artists
           @param artist_id as int
           @param cancellable as Gio.Cancellable
           @return [(str, str)] : list of (artist, cover_uri)
        """
        artists = []
        try:
            while self.wait_for_token(cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/artists/%s/related-artists" %\
                artist_id
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]:
                    try:
                        image_uri = item["images"][1]["url"]
                    except:
                        image_uri = None
                    artists.append((item["id"],
                                    item["name"],
                                    image_uri))
        except Exception as e:
            Logger.error("SpotifySearch::get_similar_artists(): %s", e)
        return artists

    def search(self, search, cancellable):
        """
            Get tracks/artists/albums related to search
            We need a thread because we are going to populate DB
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        try:
            storage_type = StorageType.SEARCH | StorageType.EPHEMERAL
            while self.wait_for_token(cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?"
            uri += "q=%s&type=album,track" % search
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                self.__create_from_tracks_payload(decode["tracks"]["items"],
                                                  storage_type,
                                                  cancellable)
                self.__create_albums_from_albums_payload(
                                                 decode["albums"]["items"],
                                                 storage_type,
                                                 False,
                                                 cancellable)
        except Exception as e:
            Logger.warning("SpotifySearch::search(): %s", e)
        if not cancellable.is_cancelled():
            emit_signal(self, "search-finished")

    def load_tracks(self, album_id, storage_type, cancellable):
        """
            Load tracks for album
            @param album_id as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        try:
            uri = "https://api.spotify.com/v1/albums/%s" % album_id
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                tracks_payload = decode["tracks"]["items"]
                for item in tracks_payload:
                    item["album"] = decode
                self.__create_from_tracks_payload(tracks_payload,
                                                  storage_type,
                                                  cancellable)
        except Exception as e:
            Logger.warning("SpotifySearch::load_tracks(): %s", e)

    def stop(self):
        """
            Stop db populate
        """
        if not self.__cancellable.is_cancelled():
            self.__cancellable.cancel()

    @property
    def is_running(self):
        """
            Return populate status
        """
        return self.__is_running

#######################
# PRIVATE             #
#######################
    def __populate_db(self):
        """
            Populate DB in a background task
        """
        try:
            Logger.info("Spotify download started")
            self.__is_running = True
            self.__cancellable = Gio.Cancellable()
            storage_types = []
            # Check if storage type needs to be updated
            # Check if albums newer than a week are enough
            timestamp = time() - 604800
            for storage_type in [StorageType.SPOTIFY_NEW_RELEASES,
                                 StorageType.SPOTIFY_SIMILARS]:
                newer_albums = App().albums.get_newer_for_storage_type(
                                                           storage_type,
                                                           timestamp)
                if len(newer_albums) < self.__MIN_ITEMS_PER_STORAGE_TYPE:
                    storage_types.append(storage_type)
            # Update needed storage types
            if storage_types:
                for storage_type in storage_types:
                    if storage_type == StorageType.SPOTIFY_NEW_RELEASES:
                        self.search_new_releases(self.__cancellable)
                    else:
                        self.search_similar_albums(self.__cancellable)
                self.clean_old_albums(storage_types)
            Logger.info("Spotify download finished")
        except Exception as e:
            Logger.error("SpotifySearch::__populate_db(): %s", e)
        self.__is_running = False

    def clean_old_albums(self, storage_types):
        """
            Clean old albums from DB
            @param storage_types as [StorageType]
        """
        SqlCursor.add(App().db)
        # Remove older albums
        for storage_type in storage_types:
            # If too many albums, do some cleanup
            count = App().albums.get_count_for_storage_type(storage_type)
            diff = count - self.__MAX_ITEMS_PER_STORAGE_TYPE
            if diff > 0:
                album_ids = App().albums.get_oldest_for_storage_type(
                    storage_type, diff)
                for album_id in album_ids:
                    App().tracks.remove_album(album_id, False)
        # On cancel, clean not needed, done in Application::quit()
        if not self.__cancellable.is_cancelled():
            App().tracks.clean(False)
            App().albums.clean(False)
            App().artists.clean(False)
        SqlCursor.commit(App().db)
        SqlCursor.remove(App().db)

    def __get_artist_albums_payload(self, spotify_id, cancellable):
        """
            Get albums payload for artist
            @param spotify_id as str
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            while self.wait_for_token(cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/artists/%s/albums" % spotify_id
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                return decode["items"]
        except Exception as e:
            Logger.warning(
                "SpotifySearch::__get_artist_albums_payload(): %s", e)
        return None

    def __get_track_payload(self, helper, spotify_id, cancellable):
        """
            Get track payload
            @param helper as TaskHelper
            @param spotify_id as str
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            uri = "https://api.spotify.com/v1/tracks/%s" % spotify_id
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                return json.loads(data.decode("utf-8"))
        except Exception as e:
            Logger.error("SpotifySearch::__get_track_payload(): %s", e)
        return {}

    def __download_cover(self, album_id, cover_uri, storage_type, cancellable):
        """
            Create album and download cover
            @param album_id as int
            @param cover_uri as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        try:
            if cancellable.is_cancelled():
                return
            album = Album(album_id)
            if App().art.get_album_artwork_uri(album) is None and\
                    cover_uri is not None:
                (status, data) = App().task_helper.load_uri_content_sync(
                                                        cover_uri,
                                                        cancellable)
                if status:
                    App().art.save_album_artwork(data, album)
            emit_signal(self, "match-album", album_id, storage_type)
        except Exception as e:
            Logger.error(
                "SpotifySearch::__download_cover(): %s", e)

    def __create_from_tracks_payload(self, payload, storage_type,
                                     cancellable):
        """
            Create albums from a track payload
            @param payload as {}
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        # Populate tracks
        for item in payload:
            if not storage_type & StorageType.EPHEMERAL:
                cancellable_sleep(2, cancellable)
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            track_id = App().tracks.get_id_for_mb_track_id(item["id"])
            if track_id < 0:
                track_id = self.__save_track(item, storage_type)
            emit_signal(self, "match-track", track_id, storage_type)

    def __create_albums_from_albums_payload(self, payload, storage_type,
                                            load_tracks, cancellable):
        """
            Create albums from albums payload
            @param payload as {}
            @param storage_type as StorageType
            @param load_tracks as bool
            @param cancellable as Gio.Cancellable
        """
        # Populate tracks
        for album_item in payload:
            if not storage_type & StorageType.EPHEMERAL:
                cancellable_sleep(2, cancellable)
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            album_id = App().albums.get_id_for_mb_album_id(album_item["id"])
            if album_id >= 0:
                emit_signal(self, "match-album", album_id, storage_type)
                continue
            (album_saved, album_id,
             album_artist_ids,
             added_album_artist_ids) = self.__save_album(album_item,
                                                         storage_type)
            if load_tracks:
                album = Album(album_id)
                album.load_tracks(cancellable)
            self.__download_cover(album_id,
                                  album_item["images"][0]["url"],
                                  storage_type,
                                  cancellable)

    def __save_album(self, payload, storage_type):
        """
            Save album payload to DB
            @param payload as {}
            @param storage_type as StorageType
            @return track_id as int
        """
        spotify_id = payload["id"]
        uri = "web://%s" % spotify_id
        total_tracks = payload["total_tracks"]
        album_artists = []
        for artist in payload["artists"]:
            album_artists.append(artist["name"])
        album_artists = ";".join(album_artists)
        album_name = payload["name"]
        mtime = int(time())
        Logger.debug("SpotifySearch::__save_album(): %s - %s",
                     album_artists, album_name)
        return App().scanner.save_album(
                        album_artists,
                        "", "", album_name,
                        spotify_id, uri, 0, 0, 0,
                        # HACK: Keep total tracks in sync int field
                        total_tracks, mtime, storage_type)

    def __save_track(self, payload, storage_type):
        """
            Save track payload to DB
            @param payload as {}
            @param storage_type as StorageType
            @return track_id as int
        """
        spotify_id = payload["id"]
        title = payload["name"]
        _artists = []
        for artist in payload["artists"]:
            _artists.append(artist["name"])
        _album_artists = []
        for artist in payload["album"]["artists"]:
            _album_artists.append(artist["name"])
        Logger.debug("SpotifySearch::__save_track(): %s - %s",
                     _artists, title)
        # Translate to tag value
        artists = ";".join(_artists)
        album_artists = ";".join(_album_artists)
        spotify_album_id = payload["album"]["id"]
        total_tracks = payload["album"]["total_tracks"]
        album_name = payload["album"]["name"]
        discnumber = int(payload["disc_number"])
        discname = None
        tracknumber = int(payload["track_number"])
        try:
            release_date = "%sT00:00:00" % payload["album"]["release_date"]
            dt = GLib.DateTime.new_from_iso8601(release_date,
                                                GLib.TimeZone.new_local())
            timestamp = dt.to_unix()
            year = dt.get_year()
        except:
            timestamp = None
            year = None
        duration = payload["duration_ms"]
        uri = "web://%s" % spotify_id
        mtime = int(time())
        (album_saved, album_id,
         album_artist_ids, added_album_artist_ids) = App().scanner.save_album(
                        album_artists,
                        "", "", album_name,
                        spotify_album_id, uri, 0, 0, 0,
                        # HACK: Keep total tracks in sync int field
                        total_tracks, mtime, storage_type)
        (track_id, album_id) = App().scanner.save_track(
                   None, artists, "", "",
                   uri, title, duration, tracknumber, discnumber,
                   discname, year, timestamp, mtime, 0,
                   0, 0, 0, spotify_id,
                   0, album_saved, album_id, album_artist_ids,
                   added_album_artist_ids, storage_type)
        return track_id
