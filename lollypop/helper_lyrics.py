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

from gi.repository import Gio

from lollypop.logger import Logger


class SyncLyricsHelper:
    """
        Sync lyrics helper
    """

    def __init__(self):
        """
            Init helper
        """
        self.__timestamps = {}

    def load(self, track):
        """
            Load lyrics for track
            @param track as Track
        """
        self.__track = track
        self.__timestamps = {}
        uri_no_ext = ".".join(track.uri.split(".")[:-1])
        self.__lrc_file = Gio.File.new_for_uri(uri_no_ext + ".lrc")
        if self.__lrc_file.query_exists():
            self.__get_timestamps()
        else:
            from lollypop.tagreader import Discoverer, TagReader
            discoverer = Discoverer()
            tagreader = TagReader()
            try:
                info = discoverer.get_info(track.uri)
            except:
                info = None
            if info is not None:
                tags = info.get_tags()
                for (lyrics, timestamp) in tagreader.get_synced_lyrics(tags):
                    self.__timestamps[timestamp] = lyrics

    def get_lyrics_for_timestamp(self, timestamp):
        """
            Get lyrics for timestamp
            @param timestamp as int
            @return ([str], str, [str])
        """
        previous = []
        next = []
        current = None
        for key in self.__timestamps.keys():
            if timestamp > key and current is None:
                if len(previous) == 5:
                    previous.pop(0)
                previous.append(self.__timestamps[key])
            elif current is None and previous:
                current = previous.pop(-1)
                next.append(self.__timestamps[key])
            elif timestamp < key and len(next) != 5:
                next.append(self.__timestamps[key])
            else:
                break
        if current is None:
            current = ""
        return (previous, [" ", current, " "], next)

    @property
    def available(self):
        """
            True if lyrics available
            @return bool
        """
        return len(self.__timestamps.keys()) != 0

############
# PRIVATE  #
############
    def __str_to_timestamp(self, srt_timestamp):
        """
            Convert timestamp to time
            @timestamp as str [00:00.00]
            @return int
        """
        timestamp = int(srt_timestamp.split(".")[-1])
        seconds = int(srt_timestamp.split(".")[-2].split(":")[-1])
        minutes = int(srt_timestamp.split(".")[-2].split(":")[0])
        timestamp += seconds * 1000
        timestamp += minutes * 60000
        return timestamp

    def __get_timestamps(self):
        """
            Get timestamps from file
        """
        try:
            status = False
            if self.__lrc_file.query_exists():
                (status, content, tag) = self.__lrc_file.load_contents()
            if status:
                data = content.decode("utf-8").split("\n")
                for line in data:
                    if line.find("length") != -1:
                        continue
                    try:
                        str_timestamp = line.split("]")[0].split("[")[1]
                        timestamp = self.__str_to_timestamp(str_timestamp)
                        lyrics = " ".join(line.split("]")[1:])
                        self.__timestamps[timestamp] = lyrics
                    except:
                        continue
        except Exception as e:
            Logger.error("SyncLyricsHelper::__get_timestamps(): %s", e)
