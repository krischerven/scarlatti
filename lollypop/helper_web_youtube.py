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

from lollypop.define import App, GOOGLE_API_ID
from lollypop.utils import get_network_available, get_page_score
from lollypop.logger import Logger


class YouTubeHelper:
    """
        YoutTube helper
    """

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
        youtube_id = None
        if self.__fallback:
            if get_network_available("STARTPAGE"):
                youtube_id = self.__get_youtube_id_start(track, cancellable)
            elif get_network_available("DUCKDUCKGO"):
                youtube_id = self.__get_youtube_id_duckduck(track, cancellable)
        else:
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
            proxy = GLib.environ_getenv(GLib.get_environ(), "all_proxy")
            if proxy is not None and proxy.startswith("socks://"):
                proxy = proxy.replace("socks://", "socks4://")
            if App().settings.get_value("recent-youtube-dl"):
                python_path = GLib.get_user_data_dir() + "/lollypop/python"
                path = "%s/bin/youtube-dl" % python_path
                env = ["PYTHONPATH=%s" % python_path]
            else:
                path = "youtube-dl"
                env = []
            # Remove playlist args
            uri = sub("list=.*", "", track.uri)
            argv_list = [
                [path, "-g", "-f", "bestaudio", uri],
                [path, "-g", uri]]
            for argv in argv_list:
                if proxy is not None:
                    argv += ["--proxy", proxy, None]
                else:
                    argv.append(None)
                (s, o, e, s) = GLib.spawn_sync(None,
                                               argv,
                                               env,
                                               GLib.SpawnFlags.SEARCH_PATH,
                                               None)
                if o:
                    return o.decode("utf-8")
            error = e.decode("utf-8")
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
                best = 10000000
                for i in decode["items"]:
                    score = get_page_score(i["snippet"]["title"],
                                           track.name,
                                           track.artists[0],
                                           track.album.name)
                    if score == -1 or score == best:
                        continue
                    elif score < best:
                        best = score
                    dic[score] = i["id"]["videoId"]
                # Return url from first dic item
                if best == 10000000:
                    return None
                else:
                    return dic[best]
        except Exception as e:
            Logger.warning("YouTubeHelper::__get_youtube_id(): %s", e)
            self.__fallback = True
            return self.get_uri(track, cancellable)
        return None

    def __get_youtube_id_start(self, track, cancellable):
        """
            Get youtube id via startpage
            @param track as Track
            @param cancellable as Gio.Cancellable
            @return youtube id as str
        """
        try:
            from bs4 import BeautifulSoup
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
            uri = "https://www.startpage.com/do/search?query=%s" % search
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if not status:
                return None

            html = data.decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            ytems = []
            for link in soup.findAll("a"):
                href = link.get("href")
                title = link.get_text()
                if href is None or title is None or\
                        href.find("youtube.com/watch?v") == -1:
                    continue
                youtube_id = href.split("watch?v=")[1]
                ytems.append((youtube_id, title))
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
            Logger.warning("YouTubeHelper::__get_youtube_id_start(): %s", e)
        return None

    def __get_youtube_id_duckduck(self, track, cancellable):
        """
            Get youtube id via duckduckgo
            @param track as Track
            @param cancellable as Gio.Cancellable
            @return youtube id as str
        """
        try:
            from bs4 import BeautifulSoup
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
            uri = "https://duckduckgo.com/lite/?q=%s" % search
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if not status:
                return None

            html = data.decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            ytems = []
            for link in soup.findAll("a"):
                href = GLib.uri_unescape_string(link.get("href"), None)
                title = link.get_text()
                if href is None or title is None or\
                        href.find("youtube.com/watch?v") == -1:
                    continue
                youtube_id = href.split("watch?v=")[1]
                ytems.append((youtube_id, title))
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
            Logger.warning("YouTubeHelper::__get_youtube_id_duckduck(): %s", e)
        return None
