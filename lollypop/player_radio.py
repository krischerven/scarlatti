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

from gi.repository import TotemPlParser, Gst, Gio, GLib

from lollypop.define import App
from lollypop.logger import Logger
from lollypop.utils import emit_signal


class RadioPlayer:
    """
        Radio player
    """

    def __init__(self):
        """
            Init radio player
        """
        pass

    def load(self, track):
        """
            Load radio at uri
            @param track as Track
        """
        if Gio.NetworkMonitor.get_default().get_network_available():
            try:
                # If a web track is loading, indicate lollypop to stop loading
                # indicator
                if self._current_track.is_web:
                    emit_signal(self, "loading-changed", False,
                                self._current_track.album)
                emit_signal(self, "loading-changed", True, track.album)
                self._current_track = track
                if track.uri.find("youtu.be") != -1 or\
                        track.uri.find("youtube.com") != -1:
                    App().task_helper.run(self.__load_youtube_track, track)
                else:
                    parser = TotemPlParser.Parser.new()
                    parser.connect("entry-parsed", self.__on_entry_parsed,
                                   track)
                    parser.parse_async(track.uri, True,
                                       None, self.__on_parse_finished,
                                       track)
            except Exception as e:
                Logger.error("RadioPlayer::load(): %s" % e)
            if self.is_party:
                self.set_party(False)

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __load_youtube_track(self, track):
        """
            Load YouTube track
            @param track as Track
        """
        from lollypop.helper_web_youtube import YouTubeHelper
        helper = YouTubeHelper()
        uri = helper.get_uri_content(track)
        if uri is not None:
            track.set_uri(uri)
            GLib.idle_add(self.__start_playback, track, True)
        else:
            self.stop()

    def __start_playback(self, track):
        """
            Start playing track
            @param track as Track
        """
        self._playbin.set_state(Gst.State.NULL)
        self._playbin.set_property("uri", track.uri)
        App().radios.set_more_popular(track.id)
        self._current_track = track
        self._playbin.set_state(Gst.State.PLAYING)
        emit_signal(self, "status-changed")

    def __on_parse_finished(self, parser, result, track):
        """
            Play stream
            @param parser as TotemPlParser.Parser
            @param result as Gio.AsyncResult
            @param track as Track
        """
        # Only start playing if context always True
        if self._current_track == track:
            self.__start_playback(track)
        else:
            emit_signal(self, "loading-changed", False, track.album)

    def __on_entry_parsed(self, parser, uri, metadata, track):
        """
            Play stream
            @param parser as TotemPlParser.Parser
            @param track uri as str
            @param metadata as GLib.HastTable
            @param track as Track
        """
        # Only start playing if context always True
        if self._current_track == track:
            track.set_uri(uri)
        else:
            emit_signal(self, "loading-changed", False, track.album)
