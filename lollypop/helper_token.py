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

from gi.repository import Soup

import json
from base64 import b64encode
from time import time

from lollypop.logger import Logger
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET, App


class TokenHelper:
    """
        Get token from web services
    """

    def __init__(self):
        """
            Init object
        """
        self.__token_expires = {"SPOTIFY": 0}
        self.__tokens = {"SPOTIFY": None}
        self.__loading_token = {"SPOTIFY": False}

    def wait_for_token(self, token_name, cancellable):
        """
            True if should wait for token
            @param token_name as str
            @param cancellable as Gio.Cancellable
            @return bool
        """
        def on_token(token):
            self.__loading_token[token_name] = False
        # Remove 60 seconds to be sure
        wait = int(time()) + 60 > self.__token_expires[token_name] or\
            self.__tokens[token_name] is None
        if wait and not self.__loading_token[token_name]:
            self.__loading_token[token_name] = True
            App().task_helper.run(self.__get_token, token_name, cancellable,
                                  callback=(on_token,))
        return wait

    @property
    def spotify(self):
        """
            Get Spotify Token
            Be sure to call wait for token before trying to get this property
            @return str
        """
        return self.__tokens["SPOTIFY"]

#######################
# PRIVATE             #
#######################
    def __get_token(self, token_name, cancellable):
        """
            Get token for name
            @param token_name as str
            @param cancellable as Gio.Cancellable
        """
        # Only one token type handled for now
        self.__get_spotify_token(cancellable)

    def __get_spotify_token(self, cancellable):
        """
            Get a new auth token
            @param cancellable as Gio.Cancellable
        """
        try:
            def on_response(uri, status, data):
                try:
                    decode = json.loads(data.decode("utf-8"))
                    self.__token_expires["SPOTIFY"] = int(time()) +\
                        int(decode["expires_in"])
                    self.__tokens["SPOTIFY"] = decode["access_token"]
                except Exception as e:
                    Logger.error("SpotifySearch::get_token(): %s", e)
            token_uri = "https://accounts.spotify.com/api/token"
            credentials = "%s:%s" % (SPOTIFY_CLIENT_ID, SPOTIFY_SECRET)
            encoded = b64encode(credentials.encode("utf-8"))
            credentials = encoded.decode("utf-8")
            data = {"grant_type": "client_credentials"}
            msg = Soup.form_request_new_from_hash("POST", token_uri, data)
            msg.request_headers.append("Authorization",
                                       "Basic %s" % credentials)
            App().task_helper.send_message(msg, cancellable, on_response)
        except Exception as e:
            Logger.error("TokenHelper::__get_spotify_token(): %s", e)
