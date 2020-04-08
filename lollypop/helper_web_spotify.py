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

from gi.repository import GLib, GObject

from time import sleep
import json
from locale import getdefaultlocale

from lollypop.helper_task import TaskHelper
from lollypop.logger import Logger
from lollypop.helper_web_save import SaveWebHelper
from lollypop.define import App


class SpotifyWebHelper(GObject.Object, SaveWebHelper):
    """
       Web helper for Spotify
    """

    __gsignals__ = {
        "match-album": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-track": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "match-artist": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init helper
        """
        GObject.Object.__init__(self)
        SaveWebHelper.__init__(self)

    def get_artist_id(self, artist_name, cancellable):
        """
            Get artist id
            @param artist_name as str
            @param cancellable as Gio.Cancellable
        """
        try:
            while App().token_helper.wait_for_token("SPOTIFY", cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            artist_name = GLib.uri_escape_string(
                artist_name, None, True).replace(" ", "+")
            token = "Bearer %s" % App().token_helper.spotify
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?q=%s&type=artist" %\
                artist_name
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    return item["id"]
        except Exception as e:
            Logger.error("SpotifyWebHelper::get_artist_id(): %s", e)
        return None

    def get_track_payload(self, spotify_id, cancellable):
        """
            Get track payload for spotify id
            @param spotify_id as str
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            while App().token_helper.wait_for_token("SPOTIFY", cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % App().token_helper.spotify
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/tracks/%s" % spotify_id
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                return decode
        except Exception as e:
            Logger.error("SpotifyWebHelper::get_track_payload(): %s", e)
        return None

    def get_artist_top_tracks(self, spotify_id, cancellable):
        """
            Get top tracks for spotify id
            @param spotify_id as str
            @param cancellable as Gio.Cancellable
            @return str
        """
        try:
            locale = getdefaultlocale()[0][0:2]
            track_ids = []
            while App().token_helper.wait_for_token("SPOTIFY", cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % App().token_helper.spotify
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/artists/%s/top-tracks" %\
                spotify_id
            uri += "?country=%s" % locale
            (status, data) = helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["tracks"]:
                    track_ids.append(item["id"])
        except Exception as e:
            Logger.error("SpotifyWebHelper::get_artist_top_tracks(): %s", e)
        return track_ids

    def load_tracks(self, album_id, storage_type, cancellable):
        """
            Load tracks for album
            @param album_id as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        try:
            while App().token_helper.wait_for_token("SPOTIFY", cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            uri = "https://api.spotify.com/v1/albums/%s" % album_id
            token = "Bearer %s" % App().token_helper.spotify
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                tracks_payload = decode["tracks"]["items"]
                for item in tracks_payload:
                    item["album"] = decode
                self.save_tracks_payload_to_db(tracks_payload,
                                               storage_type,
                                               False,
                                               cancellable)
        except Exception as e:
            Logger.warning("SpotifyWebHelper::load_tracks(): %s", e)

#######################
# PRIVATE             #
#######################
