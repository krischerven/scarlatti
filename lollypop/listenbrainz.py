# Copyright (c) 2018 Philipp Wolfer <ph.wolfer@gmail.com>
# Copyright (c) 2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Soup, GObject, GLib

import json
import time
from pickle import load, dump

from lollypop.logger import Logger
from lollypop.define import App, LOLLYPOP_DATA_PATH
from lollypop.utils import get_network_available

HOST_NAME = "api.listenbrainz.org"
PATH_SUBMIT = "/1/submit-listens"


class ListenBrainz(GObject.GObject):
    """
        Submit listens to ListenBrainz.org.

        See https://listenbrainz.readthedocs.io/en/latest/dev/api.html
    """

    user_token = GObject.Property(type=str, default=None)

    def __init__(self):
        """
            Init ListenBrainz object
        """
        GObject.GObject.__init__(self)
        try:
            self.__queue_id = None
            self.__queue = load(
                open(LOLLYPOP_DATA_PATH + "/listenbrainz_queue.bin", "rb"))
        except Exception as e:
            Logger.info("LastFM::__init__(): %s", e)
            self.__queue = []
        self.__next_request_time = 0

    def listen(self, track, time):
        """
            Submit a listen for a track
            @param track as Track
            @param time as int
        """
        if not get_network_available("MUSICBRAINZ") and\
                get_network_available():
            return
        if track.id is None or track.id < 0:
            return
        payload = self.__get_payload(track)
        payload[0]["listened_at"] = time
        if App().settings.get_value("disable-scrobbling") or\
                not get_network_available("MUSICBRAINZ"):
            self.__queue.append(("single", payload))
        else:
            self.__submit("single", payload)
            self.__clean_queue()

    def playing_now(self, track):
        """
            Submit a playing now notification for a track
            @param track as Track
        """
        if App().settings.get_value("disable-scrobbling"):
            return
        if track.id is None or track.id < 0:
            return
        payload = self.__get_payload(track)
        self.__submit("playing_now", payload)

    def save(self):
        """
            Save queue to disk
        """
        with open(LOLLYPOP_DATA_PATH + "/listenbrainz_queue.bin", "wb") as f:
            dump(list(self.__queue), f)

    @property
    def can_love(self):
        """
            True if engine can love
            @return bool
        """
        return False

    @property
    def available(self):
        """
            True if service available
            @return bool
        """
        return self.user_token != ""

#######################
# PRIVATE             #
#######################
    def __clean_queue(self):
        """
            Send tracks in queue
        """
        def queue():
            if self.__queue:
                (listen_type, payload) = self.__queue.pop(0)
                App().task_helper.run(self.__request, listen_type, payload)
                return True
            self.__queue_id = None

        if self.__queue_id is None:
            self.__queue_id = GLib.timeout_add(1000, queue)

    def __submit(self, listen_type, payload):
        """
            Submit payload to service in a thread
            @param listen_type as str
            @param payload as []
        """
        App().task_helper.run(self.__request, listen_type, payload)

    def __request(self, listen_type, payload, retry=0):
        """
            Submit payload to service
            @param listen_type as str
            @param payload as []
            @param retry as int (internal)
        """
        self.__wait_for_ratelimit()
        Logger.debug("ListenBrainz %s: %r" % (listen_type, payload))
        data = {
            "listen_type": listen_type,
            "payload": payload
        }
        body = json.dumps(data).encode("utf-8")
        session = Soup.Session.new()
        uri = "https://%s%s" % (HOST_NAME, PATH_SUBMIT)
        msg = Soup.Message.new("POST", uri)
        msg.set_request("application/json",
                        Soup.MemoryUse.STATIC,
                        body)
        msg.request_headers.append("Authorization",
                                   "Token %s" % self.user_token)
        try:
            status = session.send_message(msg)
            response_headers = msg.get_property("response-headers")
            self.__handle_ratelimit(response_headers)
            # Too Many Requests
            if status == 429 and retry < 5:
                self.__request(listen_type, payload, retry + 1)
        except Exception as e:
            print("ListenBrainz::__submit():", e)

    def __wait_for_ratelimit(self):
        """
            Sleep to respect service X-RateLimit
        """
        now = time.time()
        if self.__next_request_time > now:
            delay = self.__next_request_time - now
            Logger.debug("ListenBrainz rate limit applies, delay %d" % delay)
            time.sleep(delay)

    def __handle_ratelimit(self, response):
        """
            Set rate limit from response
            @param response as Soup.MessageHeaders
        """
        remaining = response.get("X-RateLimit-Remaining")
        reset_in = response.get("X-RateLimit-Reset-In")
        if remaining is None or reset_in is None:
            return
        Logger.debug("ListenBrainz X-RateLimit-Remaining: %s" % remaining)
        Logger.debug("ListenBrainz X-RateLimit-Reset-In: %s" % reset_in)
        if (int(remaining) == 0):
            self.__next_request_time = time.time() + int(reset_in)

    def __get_payload(self, track):
        """
            Build payload from track
            @param track as Track
        """
        payload = {
            "track_metadata": {
                "artist_name": track.artists[0],
                "track_name": track.title,
                "release_name": track.album_name,
                "additional_info": {
                    "artist_mbids": [
                        mbid for mbid in track.mb_artist_ids if mbid
                    ],
                    "release_mbid": track.album.mb_album_id,
                    "recording_mbid": track.mb_track_id,
                    "tracknumber": track.number
                }
            }
        }
        return [payload]
