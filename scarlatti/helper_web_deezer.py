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

from scarlatti.logger import Logger
from scarlatti.define import App


class DeezerWebHelper:
    """
        Web helper for Deezer
    """

    def __init__(self):
        """
            Init helper
        """
        pass

    def get_artist_id(self, artist_name, cancellable):
        """
            Get artist id
            @param artist_name as str
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            uri = "https://api.deezer.com/search/artist?q=%s" % artist_name
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for artist in decode["data"]:
                    return artist["id"]
        except Exception as e:
            Logger.warning("DeezerWebHelper::get_artist_id(): %s", e)
        return None

    def get_album_payload(self, album_id, cancellable):
        """
            Get album payload for id
            @param album_id as int
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            uri = "https://api.deezer.com/album/%s" % album_id
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                return decode
        except Exception as e:
            Logger.warning("DeezerWebHelper::get_album_payload(): %s", e)
        return None

    def get_track_payload(self, track_id, cancellable):
        """
            Get album payload for id
            @param album_id as int
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            uri = "https://api.deezer.com/track/%s" % track_id
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                return decode
        except Exception as e:
            Logger.warning("DeezerWebHelper::get_track_payload(): %s", e)
        return None

    def scarlatti_album_payload(self, payload):
        """
            Convert payload to Scarlatti one
            @param payload as {}
            return {}
        """
        scarlatti_payload = {}
        scarlatti_payload["mbid"] = None
        scarlatti_payload["name"] = payload["title"]
        scarlatti_payload["uri"] = "dz:%s" % payload["id"]
        scarlatti_payload["artists"] = payload["artist"]["name"]
        scarlatti_payload["track-count"] = payload["nb_tracks"]
        scarlatti_payload["artwork-uri"] = payload["cover_big"]
        try:
            scarlatti_payload["date"] = "%sT00:00:00" % payload["release_date"]
        except:
            scarlatti_payload["date"] = None
        return scarlatti_payload

    def scarlatti_track_payload(self, payload):
        """
            Convert payload to Scarlatti one
            @param payload as {}
            @return {}
        """
        scarlatti_payload = {}
        scarlatti_payload["mbid"] = None
        scarlatti_payload["name"] = payload["title"]
        scarlatti_payload["uri"] = "dz:%s" % payload["id"]
        scarlatti_payload["artists"] = payload["artist"]["name"]
        try:
            scarlatti_payload["discnumber"] = payload["disk_number"]
        except:
            scarlatti_payload["discnumber"] = 1
        scarlatti_payload["tracknumber"] = payload["track_position"]
        scarlatti_payload["duration"] = payload["duration"] * 1000
        return scarlatti_payload

#######################
# PRIVATE             #
#######################
