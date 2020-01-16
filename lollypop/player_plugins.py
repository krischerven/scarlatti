# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (C) 2010 Jonathan Matthew (replay gain code)
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

from gi.repository import Gst

from lollypop.define import App, ReplayGain
from lollypop.logger import Logger


class PluginsPlayer:
    """
        Replay gain player
    """

    def __init__(self, playbin):
        """
            Init playbin
            @param playbin as Gst.bin
        """
        self.__equalizer = None
        self.__playbin = playbin
        self.build_audiofilter()

    def build_audiofilter(self):
        """
            Build audio filter
        """
        try:
            self.__playbin.set_property("audio-filter", None)
            audiofilter = Gst.ElementFactory.make("bin", None)
            # Internal volume manager
            self.volume = Gst.ElementFactory.make("volume", None)
            self.volume.props.volume = 0.0
            audiofilter.add(self.volume)
            # Equalizer
            self.__equalizer = None
            if App().settings.get_value("equalizer-enabled"):
                self.__equalizer = Gst.ElementFactory.make("equalizer-10bands",
                                                           None)
                audiofilter.add(self.__equalizer)
                self.volume.link(self.__equalizer)
            # Replay gain
            replay_gain = App().settings.get_enum("replay-gain")
            if replay_gain != ReplayGain.NONE:
                rgvolume = Gst.ElementFactory.make("rgvolume", None)
                if replay_gain == ReplayGain.ALBUM:
                    rgvolume.props.album_mode = 1
                else:
                    rgvolume.props.album_mode = 0
                rgvolume.props.pre_amp = App().settings.get_value(
                    "replaygain").get_double()
                audiofilter.add(rgvolume)
                rglimiter = Gst.ElementFactory.make("rglimiter", None)
                audiofilter.add(rglimiter)
                rgvolume.link(rglimiter)
                pad_src = rglimiter.get_static_pad("src")
                if self.__equalizer is not None:
                    self.volume.link(self.__equalizer)
                    self.__equalizer.link(rgvolume)
                else:
                    self.volume.link(rgvolume)
            elif self.__equalizer is not None:
                pad_src = self.__equalizer.get_static_pad("src")
                self.volume.link(self.__equalizer)
            else:
                pad_src = self.volume.get_static_pad("src")
            ghost_src = Gst.GhostPad.new("src", pad_src)
            audiofilter.add_pad(ghost_src)
            pad_sink = self.volume.get_static_pad("sink")
            ghost_sink = Gst.GhostPad.new("sink", pad_sink)
            audiofilter.add_pad(ghost_sink)
            self.__playbin.set_property("audio-filter", audiofilter)
            if self.__equalizer is not None:
                self.update_equalizer()
        except Exception as e:
            Logger.error("PluginsPlayer::init():", e)

    def update_equalizer(self):
        """
            Update equalizer based on current settings
        """
        i = 0
        for value in App().settings.get_value("equalizer"):
            self.set_equalizer(i, value)
            i += 1

    def set_equalizer(self, band, value):
        """
            Set 10bands equalizer
            @param band as int
            @param value as int
        """
        try:
            if self.__equalizer is not None:
                self.__equalizer.set_property("band%s" % band, value)
        except Exception as e:
            Logger.error("PluginsPlayer::set_equalizer():", e)

#######################
# PRIVATE             #
#######################
