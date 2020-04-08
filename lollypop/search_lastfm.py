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

import json

from lollypop.logger import Logger
from lollypop.utils import emit_signal
from lollypop.helper_web_save import SaveWebHelper
from lollypop.define import StorageType, LASTFM_API_KEY, App


class LastFMSearch(SaveWebHelper):
    """
        Search for LastFM
        We are not using pylast here, too slow: one request per method()
    """

    def __init__(self):
        """
            Init object
        """
        SaveWebHelper.__init__(self)

    def search(self, search, cancellable):
        """
            Get albums for search
            We need a thread because we are going to populate DB
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        try:
            storage_type = StorageType.SEARCH | StorageType.EPHEMERAL
            uri = "http://ws.audioscrobbler.com/2.0/?method=album.search"
            uri += "&album=%s&api_key=%s&format=json %" % (
                search, LASTFM_API_KEY)
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            albums = []
            if status:
                decode = json.loads(data.decode("utf-8"))
                query = decode["results"]["opensearch:Query"]
                for album in query["albummatches"]:
                    albums.append((album["name"], album["artist"]))
            for (album, artist) in albums:
                uri = "http://ws.audioscrobbler.com/2.0/?method=album.getinfo"
                uri += "&api_key=%s&artist=%s&album=%s&format=json" % (
                    LASTFM_API_KEY, artist, album)
                (status, data) = App().task_helper.load_uri_content_sync(
                    uri, cancellable)
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    payload = self.__get_spotify_payload(album)
                    self.save_tracks_payload_to_db(payload,
                                                   storage_type,
                                                   False,
                                                   cancellable)
        except Exception as e:
            Logger.warning("LastFMSearch::search(): %s", e)
        if not cancellable.is_cancelled():
            emit_signal(self, "finished")

    def load_tracks(self, album_id, storage_type, cancellable):
        pass

#######################
# PRIVATE             #
#######################
    def __get_spotify_payload(self, payload, cancellable):
        """
            Convert tracks to a Spotify payload
            @param payload as {}
            @param cancellable as Gio.Cancellable
            return [{}]
        """
        tracks = []
        album_payload = {}
        album_payload["id"] = "lf:%s" % payload["album"]["mbid"]
        album_payload["name"] = payload["album"]["name"]
        album_payload["artists"] = [{"name": payload["album"]["artist"]}]
        album_payload["total_tracks"] = len(payload["album"]["tracks"])
        album_payload["release_date"] = None
        try:
            artwork_uri = payload["image"][-1]["#text"]
        except:
            artwork_uri = None
        album_payload["images"] = [{"url": artwork_uri}]
        i = 1
        for track in payload["album"]["tracks"]:
            track_payload = {}
            track_payload["id"] = "lf:%s" % track["mbid"]
            track_payload["name"] = track["name"]
            track_payload["artists"] = [{"name": track["artist"]}]
            track_payload["disc_number"] = "1"
            track_payload["track_number"] = i
            track_payload["duration_ms"] = track["duration"] * 1000
            i += 1
            track_payload["album"] = album_payload
            tracks.append(track_payload)
        return tracks
