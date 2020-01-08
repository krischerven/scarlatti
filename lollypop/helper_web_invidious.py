# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib

import json

from lollypop.define import App
from lollypop.utils import get_page_score
from lollypop.logger import Logger


class InvidiousHelper:
    """
        Invidious helper
    """

    __BAD_SCORE = 1000000
    __SEARCH = "api/v1/search?q=%s"
    __VIDEO = "api/v1/videos/%s"

    def __init__(self):
        """
            Init heApper
        """
        self.__server = App().settings.get_value(
            "invidious-server").get_string().strip("/")

    def get_uri(self, track, cancellable):
        """
            Item youtube uri for web uri
            @param track as Track
            @return uri as str
            @param cancellable as Gio.Cancellable
        """
        youtube_id = self.__get_youtube_id(track, cancellable)
        if youtube_id is None:
            return ""
        else:
            return "https://www.youtube.com/watch?v=%s" % youtube_id

    def get_uri_content(self, track):
        """
            Get content uri
            @param track as Track
            @return content uri as str/None
        """
        try:
            youtube_id = track.uri.replace("https://www.youtube.com/watch?v=",
                                           "")
            video = self.__VIDEO % youtube_id
            uri = "%s/%s" % (self.__server, video)
            (status, data) = App().task_helper.load_uri_content_sync(uri)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["adaptiveFormats"]:
                    if item["container"] == "webm" and\
                            item["encoding"] == "opus":
                        return item["url"]
        except Exception as e:
            Logger.warning("InvidiousHelper::get_uri_content(): %s", e)
        return None

#######################
# PRIVATE             #
#######################
    def __get_youtube_id(self, track, cancellable):
        """
            Get YouTube id
            @param track as Track
            @param cancellable as Gio.Cancellable
            @return str
        """
        unescaped = "%s %s" % (track.artists[0],
                               track.name)
        search = GLib.uri_escape_string(
                            unescaped.replace(" ", "+"),
                            None,
                            True)
        try:
            search = self.__SEARCH % search
            uri = "%s/%s" % (self.__server, search)
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                dic = {}
                best = 10000000
                for item in decode:
                    score = get_page_score(item["title"],
                                           track.name,
                                           track.artists[0],
                                           track.album.name)
                    if score == -1 or score == best:
                        continue
                    elif score < best:
                        best = score
                    dic[score] = item["videoId"]
                # Return url from first dic item
                if best == 10000000:
                    return None
                else:
                    return dic[best]
        except Exception as e:
            Logger.warning("InvidiousHelper::__get_youtube_id(): %s", e)
        return None
