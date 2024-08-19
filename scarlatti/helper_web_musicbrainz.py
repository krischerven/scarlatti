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


class MusicBrainzWebHelper:
    """
        Web helper for MusicBrainz
    """

    def __init__(self):
        """
            Init helper
        """
        pass

    def get_tracks_payload(self, mbid, cancellable):
        """
            Get tracks payload for album mbid
            @param mbid as str
            @param cancellable as Gio.Cancellable
            @return payload as []
        """
        try:
            uri = "http://musicbrainz.org/ws/2/release/%s" % mbid
            uri += "?inc=recordings+artist-credits&fmt=json"
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                release = json.loads(data.decode("utf-8"))
                for media in release["media"]:
                    return media["tracks"]
        except:
            Logger.error(
                "MusicBrainzWebHelper::get_tracks_payload(): %s", data)
        return []

    def scarlatti_album_payload(self, payload):
        """
            Convert payload to Scarlatti one
            @param payload as {}
            return {}
        """
        scarlatti_payload = {}
        scarlatti_payload["mbid"] = None
        scarlatti_payload["name"] = payload["title"]
        scarlatti_payload["uri"] = "mb:%s" % payload["id"]
        artists = []
        for artist in payload["artist-credit"]:
            artists.append(artist["name"])
        scarlatti_payload["artists"] = ";".join(artists)
        scarlatti_payload["track-count"] = payload["media"][0]["track-count"]
        scarlatti_payload["artwork-uri"] = payload["id"]
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
        scarlatti_payload["uri"] = "mb:%s" % payload["id"]
        artists = []
        for artist in payload["artist-credit"]:
            artists.append(artist["name"])
        scarlatti_payload["artists"] = ";".join(artists)
        scarlatti_payload["discnumber"] = "1"
        scarlatti_payload["tracknumber"] = payload["position"]
        scarlatti_payload["duration"] = payload["length"]
        return scarlatti_payload

#######################
# PRIVATE             #
#######################
