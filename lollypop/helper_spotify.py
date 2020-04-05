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

from gi.repository import GLib, GObject

from time import time

from lollypop.logger import Logger
from lollypop.utils import emit_signal
from lollypop.objects_album import Album
from lollypop.define import App, Type


class SpotifyHelper(GObject.Object):
    """
        Helper for Spotify
    """

    __gsignals__ = {
        "match-album": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-track": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)

    def save_tracks_payload_to_db(self, payload, storage_type, cancellable):
        """
            Create albums from a track payload
            @param payload as {}
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        # Populate tracks
        for item in payload:
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            track_id = App().tracks.get_id_for_mb_track_id(item["id"])
            if track_id < 0:
                track_id = self.__save_track(item, storage_type)
            emit_signal(self, "match-track", track_id, storage_type)

    def save_albums_payload_to_db(self, payload, storage_type, cancellable):
        """
            Create albums from albums payload
            @param payload as {}
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        for album_item in payload:
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            album_id = App().albums.get_id_for_mb_album_id(album_item["id"])
            if album_id >= 0:
                album = Album(album_id)
                if App().art.get_album_artwork_uri(album) is None:
                    self.__download_cover(album,
                                          album_item["images"][0]["url"],
                                          storage_type,
                                          cancellable)
                else:
                    emit_signal(self, "match-album", album_id, storage_type)
                continue
            album_id = self.__save_album(album_item, storage_type)
            album = Album(album_id)
            if App().art.get_album_artwork_uri(album) is None:
                self.__download_cover(album,
                                      album_item["images"][0]["url"],
                                      storage_type,
                                      cancellable)
            else:
                emit_signal(self, "match-album", album_id, storage_type)

#######################
# PRIVATE             #
#######################
    def __download_cover(self, album, cover_uri, storage_type, cancellable):
        """
            Create album and download cover
            @param album as Album
            @param cover_uri as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        try:
            if cancellable.is_cancelled():
                return
            if App().art.get_album_artwork_uri(album) is None and\
                    cover_uri is not None:
                (status, data) = App().task_helper.load_uri_content_sync(
                                                        cover_uri,
                                                        cancellable)
                if status:
                    App().art.save_album_artwork(album, data)
            emit_signal(self, "match-album", album.id, storage_type)
        except Exception as e:
            Logger.error(
                "SpotifyHelper::__download_cover(): %s", e)

    def __save_album(self, payload, storage_type):
        """
            Save album payload to DB
            @param payload as {}
            @param storage_type as StorageType
            @return album_id as int
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
        Logger.debug("SpotifyHelper::__save_album(): %s - %s",
                     album_artists, album_name)
        item = App().scanner.save_album(
                        album_artists,
                        "", "", album_name,
                        spotify_id, uri, 0, 0, 0,
                        # HACK: Keep total tracks in sync int field
                        total_tracks, mtime, storage_type)
        App().albums.add_genre(item.album_id, Type.WEB)
        return item.album_id

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
        Logger.debug("SpotifyHelper::__save_track(): %s - %s",
                     _artists, title)
        # Translate to tag value
        artists = ";".join(_artists)
        album_artists = ";".join(_album_artists)
        if not artists:
            artists = album_artists
        spotify_album_id = payload["album"]["id"]
        total_tracks = payload["album"]["total_tracks"]
        album_name = payload["album"]["name"]
        discnumber = int(payload["disc_number"])
        discname = ""
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
        item = App().scanner.save_album(
                        album_artists,
                        "", "", album_name,
                        spotify_album_id, uri, 0, 0, 0,
                        # HACK: Keep total tracks in sync int field
                        total_tracks, mtime, storage_type)
        App().scanner.save_track(
                   item, None, artists, "", "",
                   uri, title, duration, tracknumber, discnumber,
                   discname, year, timestamp, mtime, 0, 0, 0, 0, spotify_id,
                   0, storage_type)
        return item.track_id
