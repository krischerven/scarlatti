# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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
        self.init()

    def init(self):
        """
            Init playbin
        """
        try:
            bin = Gst.ElementFactory.make("bin", "bin")

            # Internal volume manager
            self.volume = Gst.ElementFactory.make("volume", "volume")
            self.volume.props.volume = 0.0
            bin.add(self.volume)
            previous_bin = self.volume

            # Equalizer
            if App().settings.get_value("equalizer-enabled"):
                self.__equalizer = Gst.ElementFactory.make("equalizer-10bands",
                                                           "equalizer-10bands")
                bin.add(self.__equalizer)
                previous_bin.link(self.__equalizer)
                previous_bin = self.__equalizer

            # Replay gain
            replay_gain = App().settings.get_enum("replay-gain")
            if replay_gain != ReplayGain.NONE:
                rgvolume = Gst.ElementFactory.make("rgvolume", "rgvolume")
                if replay_gain == ReplayGain.ALBUM:
                    rgvolume.props.album_mode = 1
                else:
                    rgvolume.props.album_mode = 0
                rgvolume.props.pre_amp = App().settings.get_value(
                    "replaygain").get_double()
                bin.add(rgvolume)
                rglimiter = Gst.ElementFactory.make("rglimiter", "rglimiter")
                bin.add(rglimiter)
                rgvolume.link(rglimiter)
                previous_bin = rglimiter

            audiosink = Gst.ElementFactory.make("autoaudiosink",
                                                "autoaudiosink")
            bin.add(audiosink)
            previous_bin.link(audiosink)

            bin.add_pad(Gst.GhostPad.new(
                "sink",
                self.volume.get_static_pad("sink")))
            self.__playbin.set_property("audio-sink", bin)
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
