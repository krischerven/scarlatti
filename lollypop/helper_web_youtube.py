# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
from re import sub
from gettext import gettext as _

from lollypop.define import App, GOOGLE_API_ID
from lollypop.utils import escape
from lollypop.logger import Logger


class YouTubeHelper:
    """
        YoutTube helper
    """

    __BAD_SCORE = 1000000

    def __init__(self):
        """
            Init heApper
        """
        self.__fallback = False

    def get_uri(self, track, cancellable):
        """
            Item youtube uri for web uri
            @param track as Track
            @return uri as str
            @param cancellable as Gio.Cancellable
        """
        yid = self.__get_youtube_id(track, cancellable)
        if yid is None:
            return ""
        else:
            return "https://www.youtube.com/watch?v=%s" % yid

    def get_uri_content(self, track):
        """
            Get content uri
            @param track as Track
            @return content uri as str/None
        """
        try:
            python_path = GLib.get_user_data_dir() + "/lollypop/python"
            path = "%s/bin/youtube-dl" % python_path
            # Remove playlist args
            uri = sub("list=.*", "", track.uri)
            argv_list = [
                [path, "-g", "-f", "bestaudio", uri, None],
                [path, "-g", uri, None]]
            for argv in argv_list:
                (s, o, e, s) = GLib.spawn_sync(None,
                                               argv,
                                               ["PYTHONPATH=%s" % python_path],
                                               GLib.SpawnFlags.SEARCH_PATH,
                                               None)
                if o:
                    return o.decode("utf-8")
            error = e.decode("utf-8")
            if App().notify is not None:
                GLib.idle_add(App().notify.send,
                              _("Can't find this track on YouTube"))
            Logger.warning("YouTubeHelper::get_uri_content(): %s", error)
        except Exception as e:
            Logger.warning("YouTubeHelper::get_uri_content(): %s", e)
        return None

#######################
# PRIVATE             #
#######################
    def __get_youtube_id(self, track, cancellable):
        """
            Get youtube id
            @param track as Track
            @param cancellable as Gio.Cancellable
            @return youtube id as str
        """
        if self.__fallback:
            return self.__get_youtube_id_fallback(track, cancellable)
        unescaped = "%s %s" % (track.artists[0],
                               track.name)
        search = GLib.uri_escape_string(
                            unescaped.replace(" ", "+"),
                            None,
                            True)
        key = App().settings.get_value("cs-api-key").get_string()
        try:
            uri = "https://www.googleapis.com/youtube/v3/" +\
                  "search?part=snippet&q=%s&" % search +\
                  "type=video&key=%s&cx=%s" % (key, GOOGLE_API_ID)
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                dic = {}
                best = self.__BAD_SCORE
                for i in decode["items"]:
                    score = self.__get_youtube_score(i["snippet"]["title"],
                                                     track.name,
                                                     track.artists[0],
                                                     track.album.name)
                    if score < best:
                        best = score
                    elif score == best:
                        continue  # Keep first result
                    dic[score] = i["id"]["videoId"]
                # Return url from first dic item
                if best == self.__BAD_SCORE:
                    return None
                else:
                    return dic[best]
        except Exception as e:
            Logger.warning("YouTubeHelper::__get_youtube_id(): %s", e)
            self.__fallback = True
            return self.__get_youtube_id_fallback(track, cancellable)
        return None

    def __get_youtube_score(self, page_title, title, artist, album):
        """
            Calculate youtube score
            if page_title looks like (title, artist, album), score is lower
            @return int
        """
        page_title = escape(page_title.lower(), [])
        artist = escape(artist.lower(), [])
        album = escape(album.lower(), [])
        title = escape(title.lower(), [])
        # YouTube page title should be at least as long as wanted title
        if len(page_title) < len(title):
            return self.__BAD_SCORE
        # Remove common word for a valid track
        page_title = page_title.replace("official", "")
        page_title = page_title.replace("video", "")
        page_title = page_title.replace("audio", "")
        # Remove artist name
        page_title = page_title.replace(artist, "")
        # Remove album name
        page_title = page_title.replace(album, "")
        # Remove title
        page_title = page_title.replace(title, "")
        return len(page_title)

    def __get_youtube_id_fallback(self, track, cancellable):
        """
            Get youtube id (fallback)
            @param track as Track
            @param cancellable as Gio.Cancellable
            @return youtube id as str
        """
        try:
            from beautifulsoup4 import BeautifulSoup
        except:
            print("$ sudo pip3 install beautifulsoup4")
            return None
        try:
            unescaped = "%s %s" % (track.artists[0],
                                   track.name)
            search = GLib.uri_escape_string(
                            unescaped.replace(" ", "+"),
                            None,
                            True)
            uri = "https://www.youtube.com/results?search_query=%s" % search
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if not status:
                return None

            html = data.decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            ytems = []
            for link in soup.findAll("a"):
                href = link.get("href")
                title = link.get("title")
                if href is None or title is None:
                    continue
                if href.startswith("/watch?v="):
                    href = href.replace("/watch?v=", "")
                    ytems.append((href, title))
            dic = {}
            best = self.__BAD_SCORE
            for (yid, title) in ytems:
                score = self.__get_youtube_score(title,
                                                 track.name,
                                                 track.artists[0],
                                                 track.album.name)
                if score < best:
                    best = score
                elif score == best:
                    continue  # Keep first result
                dic[score] = yid
            # Return url from first dic item
            if best == self.__BAD_SCORE:
                return None
            else:
                return dic[best]
        except Exception as e:
            Logger.warning("YouTubeHelper::__get_youtube_id_fallback(): %s", e)
            self.__fallback = True
        return None
