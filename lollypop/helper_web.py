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

from pickle import load, dump
from gettext import gettext as _

from lollypop.helper_web_youtube import YouTubeHelper
from lollypop.helper_web_invidious import InvidiousHelper
from lollypop.define import CACHE_PATH, App
from lollypop.logger import Logger


class WebHelper:
    """
        Web helper
    """

    def __init__(self):
        """
            Init helper
        """
        if App().settings.get_value("invidious-server").get_string():
            self.__helpers = [InvidiousHelper()]
        else:
            self.__helpers = [YouTubeHelper()]

    def set_uri(self, track, cancellable):
        """
            Set uri for track
            @param track as Track
            @param cancellable as Gio.Cancellable
        """
        escaped = GLib.uri_escape_string(track.uri, None, True)
        # Read URI from cache
        try:
            uri = load(open("%s/web_%s" % (CACHE_PATH, escaped), "rb"))
            track.set_uri(uri)
            return
        except:
            pass

        # Get URI from helpers
        for helper in self.__helpers:
            uri = helper.get_uri(track, cancellable)
            if uri:
                Logger.info("Track found by %s" % helper)
                try:
                    # CACHE URI
                    with open("%s/web_%s" % (CACHE_PATH, escaped), "wb") as f:
                        dump(uri, f)
                except:
                    pass
                track.set_uri(uri)
                break

    def get_track_content(self, track):
        """
            Get content uri
            @param track as Track
            @return content uri as str
        """
        for helper in self.__helpers:
            uri = helper.get_uri_content(track)
            if uri:
                Logger.info("Track URI found by %s" % helper)
                return uri
        GLib.idle_add(App().notify.send, _("Can't find this track on YouTube"))
        return None
