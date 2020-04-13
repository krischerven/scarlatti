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

from hashlib import md5


class DeezerWebHelper:
    """
        Web helper for Deezer
    """

    def __init__(self):
        """
            Init helper
        """
        pass

    def lollypop_album_payload(self, payload):
        """
            Convert payload to Lollypop one
            @param payload as {}
            return {}
        """
        lollypop_payload = {}
        lollypop_payload = {}
        lollypop_payload["name"] = payload["title"]
        lollypop_payload["uri"] = "dz:%s" % payload["id"]
        lollypop_payload["artists"] = [payload["artist"]["name"]]
        lollypop_payload["track-count"] = payload["nb_tracks"]
        lollypop_payload["artwork-uri"] = payload["cover_big"]
        album_id_string = "%s-%s" % (lollypop_payload["name"],
                                     lollypop_payload["artists"])
        album_id = md5(album_id_string.encode("utf-8")).hexdigest()
        lollypop_payload["id"] = album_id
        return lollypop_payload

    def lollypop_track_payload(self, payload):
        """
            Convert payload to Lollypop one
            @param payload as {}
            @return {}
        """
        lollypop_payload = {}
        lollypop_payload["name"] = payload["title"]
        lollypop_payload["uri"] = "dz:%s" % payload["id"]
        lollypop_payload["artists"] = [payload["artist"]["name"]]
        lollypop_payload["discnumber"] = payload["disk_number"]
        lollypop_payload["tracknumber"] = payload["track_position"]
        lollypop_payload["duration"] = payload["duration"] * 1000
        track_id_string = "%s-%s-%s" % (lollypop_payload["name"],
                                        lollypop_payload["tracknumber"],
                                        lollypop_payload["artists"])
        track_id = md5(track_id_string.encode("utf-8")).hexdigest()
        lollypop_payload["id"] = track_id
        return lollypop_payload

#######################
# PRIVATE             #
#######################
