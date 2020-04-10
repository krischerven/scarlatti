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

from time import sleep
import json
from random import shuffle

from lollypop.helper_web_save import SaveWebHelper
from lollypop.logger import Logger
from lollypop.define import App


class MusicBrainzWebHelper(SaveWebHelper):
    """
        Web helper for MusicBrainz
    """

    __gsignals__ = {
        "match-album": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-track": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)
        SaveWebHelper.__init__(self)
        # MusicBrainz does not allow to get tracks by mbid
        # So keep payload here
        self.__tracks_payload = {}
        self.__albums_payload = {}

    def get_artist_id(self, artist_name, cancellable):
        """
            Get artist id
            @param artist_name as str
            @param cancellable as Gio.Cancellable
        """
        sleep(0.1)
        try:
            artist_name = GLib.uri_escape_string(
                artist_name, None, True).replace(" ", "+")
            uri = "http://musicbrainz.org/ws/2/artist/"
            uri += "?fmt=json&query=artist:%s" % artist_name
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]:
                    return item["id"]
        except:
            Logger.error("MusicBrainzWebHelper::get_artist_id(): %s", data)
        return None

    def get_artist_top_tracks(self, mbid, cancellable):
        """
            Get top tracks for mbid
            MusicBrainz does not have charts so just get random tracks
            @param mbid as str
            @param cancellable as Gio.Cancellable
            @return [str]
        """
        sleep(0.1)
        top_track_ids = []
        handled_releases = []
        try:
            uri = "http://musicbrainz.org/ws/2/release?artist=%s" % mbid
            uri += "&inc=recordings+artist-credits&fmt=json"
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for release in decode["releases"]:
                    track_ids = []
                    if release["title"].lower() in handled_releases:
                        continue
                    handled_releases.append(release["title"].lower())
                    album_payload = self.get_album_payload(release["id"])
                    if album_payload is None:
                        album_payload = self.__get_spotify_album_payload(
                                release, cancellable)
                        self.__albums_payload[release["id"]] = album_payload
                    for media in release["media"]:
                        for track in media["tracks"]:
                            if track["length"] is None or\
                                    track["length"] < 30000:
                                continue
                            payload = self.__get_spotify_track_payload(track)
                            payload["album"] = album_payload
                            track_ids.append(track["id"])
                            self.__tracks_payload[track["id"]] = payload
                        break
                    shuffle(track_ids)
                    top_track_ids += track_ids[:5]
        except:
            Logger.error("MusicBrainzWebHelper::get_artist_top_tracks(): %s",
                         data)
        shuffle(top_track_ids)
        return top_track_ids[:5]

    def get_artist_album_ids(self, mbid, cancellable):
        """
            Get artist album ids
            @param mbid as artist id
            @param cancellable as Gio.Cancellable
            @return [str]
        """
        sleep(0.1)
        album_ids = []
        try:
            uri = "http://musicbrainz.org/ws/2/release?artist=%s" % mbid
            uri += "&fmt=json"
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for release in decode["releases"]:
                    album_ids.append(release["id"])
        except:
            Logger.error(
                "MusicBrainzWebHelper::__get_release_for_group(): %s", data)
        return album_ids

    def get_album_track_ids(self, mbid, cancellable):
        """
            Get album track ids
            @param mbid as str
            @param cancellable as Gio.Cancellable
            @return [str]
        """
        sleep(0.1)
        track_ids = []
        try:
            uri = "http://musicbrainz.org/ws/2/release/%s" % mbid
            uri += "?inc=recordings+artist-credits&fmt=json"
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                release = json.loads(data.decode("utf-8"))
                for media in release["media"]:
                    for track in media["tracks"]:
                        payload = self.__get_spotify_track_payload(track)
                        album = self.__get_spotify_album_payload(
                                release, cancellable)
                        payload["album"] = album
                        track_ids.append(track["id"])
                        self.__tracks_payload[track["id"]] = payload
                    if track_ids:
                        break
        except:
            Logger.error(
                "MusicBrainzWebHelper::get_album_track_ids(): %s", data)
        return track_ids

    def get_track_payload(self, mbid):
        """
            Get track payload for mbid
            @param mbid as str
            @return {}/None
        """
        if mbid in self.__tracks_payload.keys():
            return self.__tracks_payload[mbid]
        return None

    def get_album_payload(self, mbid):
        """
            Get track payload for mbid
            @param mbid as str
            @return {}/None
        """
        if mbid in self.__albums_payload.keys():
            return self.__albums_payload[mbid]
        return None

#######################
# PRIVATE             #
#######################
    def __get_spotify_album_payload(self, payload, cancellable):
        """
            Convert payload to a Spotify payload
            @param payload as {}
            @param cancellable as Gio.Cancellable
            return {}
        """
        spotify_payload = {}
        spotify_payload["id"] = "mb:%s" % payload["id"]
        spotify_payload["name"] = payload["title"]
        spotify_payload["artists"] = []
        for artist in payload["artist-credit"]:
            spotify_payload["artists"].append({"name": artist["name"]})
        spotify_payload["total_tracks"] = payload["media"][0]["track-count"]
        try:
            spotify_payload["release_date"] = payload["date"]
        except:
            spotify_payload["release_date"] = None
        spotify_payload["images"] = [{"url": payload["id"]}]
        return spotify_payload

    def __get_spotify_track_payload(self, payload):
        """
            Convert payload to a Spotify payload
            @param track_payload as {}
            return {}
        """
        spotify_payload = {}
        spotify_payload["id"] = "mb:%s" % payload["id"]
        spotify_payload["name"] = payload["title"]
        spotify_payload["artists"] = []
        for artist in payload["artist-credit"]:
            spotify_payload["artists"].append({"name": artist["name"]})
        spotify_payload["disc_number"] = "1"
        spotify_payload["track_number"] = payload["position"]
        spotify_payload["duration_ms"] = payload["length"]
        return spotify_payload
