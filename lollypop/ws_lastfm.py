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

from gi.repository import Soup, Gio

from hashlib import md5
from pickle import load, dump

from lollypop.logger import Logger
from lollypop.utils import get_network_available
from lollypop.define import LOLLYPOP_DATA_PATH, App
from lollypop.define import LASTFM_API_KEY, LASTFM_API_SECRET


class LastFMWebService:
    """
        Handle scrobbling to Last.FM and all authenticated API calls
    """

    def __init__(self, name):
        """
            Init service
            @param name as str
        """
        self.__cancellable = Gio.Cancellable()
        self.__name = name
        try:
            self.__queue = load(
                open(LOLLYPOP_DATA_PATH + "/%s_queue.bin" % self.__name, "rb"))
        except Exception as e:
            Logger.info("LastFMWebService::__init__(): %s", e)
            self.__queue = []
        if name == "LIBREFM":
            self.__uri = "http://libre.fm/2.0/"
        else:
            self.__uri = "http://ws.audioscrobbler.com/2.0/"

    def stop(self):
        """
            Stop current tasks and save queue to disk
        """
        self.__cancellable.cancel()
        try:
            with open(LOLLYPOP_DATA_PATH + "/%s_queue.bin" % self.__name,
                      "wb") as f:
                dump(list(self.__queue), f)
        except Exception as e:
            Logger.info("LastFMWebService::stop: %s", e)

    def listen(self, track, timestamp):
        """
            Submit a listen for a track (scrobble)
            @param track as Track
            @param timestamp as int
        """
        if App().settings.get_value("disable-scrobbling") or\
                not get_network_available():
            self.__queue.append((track, timestamp))
        elif track.id is not None and track.id >= 0:
            App().task_helper.run(self.__listen, track, timestamp)

    def playing_now(self, track):
        """
            Submit a playing now notification for a track
            @param track as Track
        """
        if App().settings.get_value("disable-scrobbling") or\
                not get_network_available():
            return
        if track.id is not None and track.id >= 0:
            App().task_helper.run(self.__playing_now, track)

    def love(self, artist, title):
        """
            Love track
            @param artist as string
            @param title as string
            @thread safe
        """
        App().task_helper.run(self.__love, artist, title, True)

    def unlove(self, artist, title):
        """
            Unlove track
            @param artist as string
            @param title as string
            @thread safe
        """
        App().task_helper.run(self.__love, artist, title, False)

    def set_loved(self, track, loved):
        """
            Add or remove track from loved playlist on Last.fm
            @param track as Track
            @param loved as bool
        """
        if loved == 1:
            self.love(",".join(track.artists), track.name)
        else:
            self.unlove(",".join(track.artists), track.name)

#######################
# PRIVATE             #
#######################
    def __love(self, artist, title, status):
        """
            Love track
            @param artist as string
            @param title as string
            @param status as bool
        """
        try:
            token = App().ws_director.token_ws.get_token(
                self.__name, self.__cancellable)
            if token is None:
                return
            if status:
                args = self.__get_args_for_method("track.love")
            else:
                args = self.__get_args_for_method("track.unlove")
            args.append(("artist", artist))
            args.append(("track", title))
            args.append(("sk", token))
            api_sig = self.__get_sig_for_args(args)
            args.append(("api_sig", api_sig))
            post_data = {}
            for (name, value) in args:
                post_data[name] = value
            msg = Soup.form_request_new_from_hash("POST",
                                                  self.__uri,
                                                  post_data)
            data = App().task_helper.send_message_sync(msg, self.__cancellable)
            if data is not None:
                Logger.debug("%s: %s", self.__uri, data)
        except Exception as e:
            Logger.error("LastFMWebService::__love(): %s" % e)

    def __get_args_for_method(self, method):
        """
            Get arguments for method
            @param method as str
            @return [str]
        """
        args = [("method", method)]
        if self.__name == "LASTFM":
            args.append(("api_key", LASTFM_API_KEY))
        return args

    def __get_sig_for_args(self, args):
        """
            Get API sig for method
            @param args as [str]
            @return str
        """
        args.sort()
        api_sig = ""
        for (name, value) in args:
            api_sig += "%s%s" % (name, value)
        if self.__name == "LASTFM":
            api_sig = "%s%s" % (api_sig, LASTFM_API_SECRET)
        return md5(api_sig.encode("utf-8")).hexdigest()

    def __listen(self, track, timestamp):
        """
            Scrobble track
            @param track as Track
            @param timestamp as int
        """
        tracks = self.__queue + [(track, timestamp)]
        self.__queue = []
        try:
            for (track, timestamp) in tracks:
                token = App().ws_director.token_ws.get_token(
                    self.__name, self.__cancellable)
                if token is None:
                    return
                args = self.__get_args_for_method("track.scrobble")
                args.append(("artist", track.artists[0]))
                args.append(("track", track.name))
                args.append(("album", track.album.name))
                if track.mbid and track.mbid.find(":") == -1:
                    args.append(("mbid", track.mbid))
                args.append(("timestamp", str(timestamp)))
                args.append(("sk", token))
                api_sig = self.__get_sig_for_args(args)
                args.append(("api_sig", api_sig))
                post_data = {}
                for (name, value) in args:
                    post_data[name] = value
                msg = Soup.form_request_new_from_hash("POST",
                                                      self.__uri,
                                                      post_data)
                data = App().task_helper.send_message_sync(msg,
                                                           self.__cancellable)
                if data is not None:
                    Logger.debug("%s: %s", self.__uri, data)
        except Exception as e:
            Logger.error("LastFMWebService::__listen(): %s" % e)

    def __playing_now(self, track):
        """
            Now playing track
            @param track as Track
        """
        try:
            token = App().ws_director.token_ws.get_token(
                self.__name, self.__cancellable)
            if token is None:
                return
            args = self.__get_args_for_method("track.updateNowPlaying")
            args.append(("artist", track.artists[0]))
            args.append(("track", track.name))
            args.append(("album", track.album.name))
            if track.mbid and track.mbid.find(":") == -1:
                args.append(("mbid", track.mbid))
            args.append(("duration", str(track.duration // 1000)))
            args.append(("sk", token))
            api_sig = self.__get_sig_for_args(args)
            args.append(("api_sig", api_sig))
            post_data = {}
            for (name, value) in args:
                post_data[name] = value
            msg = Soup.form_request_new_from_hash("POST",
                                                  self.__uri,
                                                  post_data)
            data = App().task_helper.send_message_sync(msg, self.__cancellable)
            if data is not None:
                Logger.debug("%s: %s", self.__uri, data)
        except Exception as e:
            Logger.error("LastFMWebService::__playing_now(): %s" % e)
