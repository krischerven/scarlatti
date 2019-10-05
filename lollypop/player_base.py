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

from gi.repository import GObject

from lollypop.objects_track import Track


class BasePlayer(GObject.GObject):
    """
        Base player object
    """
    __gsignals__ = {
        "current-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "duration-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "loading-changed": (GObject.SignalFlags.RUN_FIRST, None,
                            (bool, GObject.TYPE_PYOBJECT)),
        "next-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "prev-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "seeked": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "status-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "volume-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "queue-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "playback-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "rate-changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int))
    }

    def __init__(self):
        """
            Init base player variables
        """
        # In case of multiple subclassing,
        # do not init variables for every subclass
        if not hasattr(self, "_albums"):
            GObject.GObject.__init__(self)
            self._base_init = True
            # Should player do crossfading
            self._crossfading = False
            self._current_track = Track()
            self._current_playback_track = Track()
            self._next_track = Track()
            self._prev_track = Track()
            # Albums in current playlist
            self._albums = []
            # For tracks from the cmd line
            self._external_tracks = []

    def set_next(self):
        """
            Set next track
        """
        pass

    def set_prev(self):
        """
            Set prev track
        """
        pass

#######################
# PRIVATE             #
#######################
