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
from time import sleep

from lollypop.logger import Logger
from lollypop.utils import emit_signal, get_network_available
from lollypop.helper_task import TaskHelper
from lollypop.helper_web_spotify import SpotifyWebHelper
from lollypop.define import App, StorageType


class SpotifySearch(SpotifyWebHelper):
    """
        Search for Spotify
    """
    def __init__(self):
        """
            Init object
        """
        SpotifyWebHelper.__init__(self)

    def get(self, search, storage_type, cancellable):
        """
            Get tracks/artists/albums related to search
            We need a thread because we are going to populate DB
            @param search as str
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        if not get_network_available("SPOTIFY"):
            emit_signal(self, "finished")
            return
        try:
            storage_type = StorageType.SEARCH | StorageType.EPHEMERAL
            while App().token_helper.wait_for_token("SPOTIFY", cancellable):
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % App().token_helper.spotify
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?"
            uri += "q=%s&type=album,track" % search
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                self.save_tracks_payload_to_db(decode["tracks"]["items"],
                                               storage_type,
                                               False,
                                               cancellable)
                self.save_albums_payload_to_db(decode["albums"]["items"],
                                               storage_type,
                                               True,
                                               cancellable)
        except Exception as e:
            Logger.warning("SpotifySearch::search(): %s", e)
        if not cancellable.is_cancelled():
            emit_signal(self, "finished")

#######################
# PRIVATE             #
#######################
