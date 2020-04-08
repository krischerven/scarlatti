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
import json

from lollypop.logger import Logger
from lollypop.utils import emit_signal
from lollypop.objects_album import Album
from lollypop.objects_track import Track
from lollypop.define import App, Type


class SaveWebHelper(GObject.Object):
    """
       Web helper for saving Spotify payloads
    """

    __gsignals__ = {
        "match-album": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-track": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-artist": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)

    def save_tracks_payload_to_db(self, payload, storage_type,
                                  match_album, cancellable,):
        """
            Create albums from a track payload
            @param payload as {}
            @param storage_type as StorageType
            @param match_album as bool
            @param cancellable as Gio.Cancellable
        """
        # Populate tracks
        artwork_uri = None
        track = None
        for item in payload:
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            track_id = App().tracks.get_id_for_mb_track_id(item["id"])
            if track_id < 0:
                track_id = self.__save_track(item, storage_type)
                track = Track(track_id)
                artwork_uri = item["album"]["images"][0]["url"]
            else:
                track = Track(track_id)
            if not match_album:
                emit_signal(self, "match-track", track_id, storage_type)
        if match_album and track is not None:
            if artwork_uri is not None:
                self.save_artwork(track,
                                  artwork_uri,
                                  cancellable)
            emit_signal(self, "match-album", track.album.id, storage_type)

    def save_albums_payload_to_db(self, payload, storage_type,
                                  save_artwork, cancellable):
        """
            Create albums from albums payload
            @param payload as {}
            @param storage_type as StorageType
            @param save_artwork as bool
            @param cancellable as Gio.Cancellable
        """
        for album_item in payload:
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            album_id = App().albums.get_id_for_mb_album_id(album_item["id"])
            if album_id >= 0:
                album = Album(album_id)
                self.save_artwork(album,
                                  album_item["images"][0]["url"],
                                  cancellable)
                emit_signal(self, "match-album", album_id, storage_type)
                continue
            album_id = self.__save_album(album_item, storage_type)
            album = Album(album_id)
            if save_artwork:
                self.save_artwork(album,
                                  album_item["images"][0]["url"],
                                  cancellable)
            emit_signal(self, "match-album", album_id, storage_type)

    def save_artwork(self, obj, cover_uri, cancellable):
        """
            Save artwork for obj
            @param obj as Album/Track
            @param cover_uri/mbid as str
            @param cancellable as Gio.Cancellable
        """
        try:
            if cancellable.is_cancelled():
                return
            if isinstance(obj, Album):
                album = obj
            else:
                album = obj.album
            if App().art.get_album_artwork_uri(album) is None:
                # We need to get URI from mbid
                if not cover_uri.startswith("http"):
                    cover_uri = self.__get_cover_art_uri(cover_uri,
                                                         cancellable)
                if cover_uri is None:
                    return
                (status, data) = App().task_helper.load_uri_content_sync(
                                                        cover_uri,
                                                        cancellable)
                if status:
                    App().art.save_album_artwork(album, data)
        except Exception as e:
            Logger.error(
                "SaveWebHelper::save_artwork(): %s", e)

#######################
# PRIVATE             #
#######################
    def __get_cover_art_uri(self, mbid, cancellable):
        """
            Get cover art URI for mbid
            @param mbid as str
            @param cancellable as Gio.Cancellable
            @return str/None
        """
        try:
            uri = "http://coverartarchive.org/release/%s" % mbid
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for image in decode["images"]:
                    if not image["front"]:
                        continue
                    return image["image"]
        except Exception as e:
            Logger.error(
                "MusicBrainzWebHelper::__get_cover_art_uri(): %s", e)
        return None

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
        Logger.debug("SpotifyWebHelper::save_album(): %s - %s",
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
        Logger.debug("SpotifyWebHelper::save_track(): %s - %s",
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
