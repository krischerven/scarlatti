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

import json
import re
from locale import getdefaultlocale

from lollypop.helper_web_save import SaveWebHelper
from lollypop.logger import Logger
from lollypop.define import App, LASTFM_API_KEY
from lollypop.utils import get_network_available


class LastFMWebHelper(SaveWebHelper):
    """
        Web helper for Last.FM
    """

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)
        SaveWebHelper.__init__(self)

    def get_artist_id(self, artist_name, cancellable):
        """
            Get artist id
            @param artist_name as str
            @param cancellable as Gio.Cancellable
            @return str/None
        """
        try:
            uri = "http://ws.audioscrobbler.com/2.0/?method=artist.getinfo"
            uri += "&artist=%s&api_key=%s&format=json" % (
                artist_name, LASTFM_API_KEY)
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                content = json.loads(data.decode("utf-8"))
                return content["artist"]["mbid"]
        except:
            Logger.error(
                "LastFMWebHelper::get_artist_id(): %s", uri)
        return None

    def get_artist_top_albums(self, artist, cancellable):
        """
            Get top albums for artist
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return [(str, str)]
        """
        artist = GLib.uri_escape_string(artist, None, True)
        albums = []
        try:
            uri = "http://ws.audioscrobbler.com/2.0/"
            uri += "?method=artist.gettopalbums"
            uri += "&artist=%s&api_key=%s&format=json" % (
                artist, LASTFM_API_KEY)
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                content = json.loads(data.decode("utf-8"))
                for album in content["topalbums"]["album"]:
                    albums.append((album["name"], album["artist"]["name"]))
        except:
            Logger.error(
                "LastFMWebHelper::get_artist_top_albums(): %s", uri)
        return albums

    def get_album_payload(self, album, artist, cancellable):
        """
            Get album payload for mbid
            @param album as str
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return {}/None
        """
        artist = GLib.uri_escape_string(artist, None, True)
        album = GLib.uri_escape_string(album, None, True)
        try:
            uri = "http://ws.audioscrobbler.com/2.0/"
            uri += "?method=album.getInfo"
            uri += "&album=%s&artist=%s&api_key=%s&format=json" % (
                album, artist, LASTFM_API_KEY)
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                return json.loads(data.decode("utf-8"))["album"]
        except:
            Logger.error(
                "LastFMWebHelper::get_album_payload(): %s", uri)
        return None

    def get_track_payload(self, mbid, cancellable):
        """
            Get track payload for mbid
            @param mbid as str
            @param cancellable as Gio.Cancellable
            @return {}/None
        """
        try:
            uri = "http://ws.audioscrobbler.com/2.0/"
            uri += "?method=track.getInfo"
            uri += "&mbid=%s&api_key=%s&format=json" % (
                mbid, LASTFM_API_KEY)
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                return json.loads(data.decode("utf-8"))["track"]
        except:
            Logger.error(
                "LastFMWebHelper::get_track_payload(): %s", uri)
        return None

    def get_artist_bio(self, artist):
        """
            Get artist biography
            @param artist as str
            @return content as bytes/None
        """
        if not get_network_available("LASTFM"):
            return None
        artist = GLib.uri_escape_string(artist, None, True)
        try:
            language = getdefaultlocale()[0][0:2]
            uri = "http://ws.audioscrobbler.com/2.0/?method=artist.getinfo"
            uri += "&artist=%s&api_key=%s&format=json&lang=%s" % (
                artist, LASTFM_API_KEY, language)
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                content = json.loads(data.decode("utf-8"))
                bio = content["artist"]["bio"]["content"]
                bio = re.sub(r"<.*Last.fm.*>.", "", bio)
                return bio.encode(encoding="UTF-8")
        except:
            Logger.error(
                "LastFMWebHelper::get_artist_bio(): %s", uri)
        return None

    def get_spotify_payload(self, album):
        """
            Convert tracks to a Spotify payload
            @param album as {}
            return [{}]
        """
        tracks = []
        album_payload = {}
        album_payload["id"] = "lf:%s-%s" % (album["artist"],
                                            album["name"])
        album_payload["name"] = album["name"]
        album_payload["artists"] = [{"name": album["artist"]}]
        album_payload["total_tracks"] = len(album["tracks"])
        album_payload["release_date"] = None
        try:
            artwork_uri = album["image"][-1]["#text"]
        except:
            artwork_uri = None
        album_payload["images"] = [{"url": artwork_uri}]
        i = 1
        for track in album["tracks"]["track"]:
            track_payload = {}
            track_payload["id"] = "lf:%s-%s-%s" % (track["artist"]["name"],
                                                   album["name"],
                                                   track["name"])
            track_payload["name"] = track["name"]
            track_payload["artists"] = [track["artist"]]
            track_payload["disc_number"] = "1"
            track_payload["track_number"] = i
            track_payload["duration_ms"] = track["duration"]
            i += 1
            track_payload["album"] = album_payload
            tracks.append(track_payload)
        return tracks

#######################
# PRIVATE             #
#######################
