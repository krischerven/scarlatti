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

from gi.repository import GObject, Gtk

from lollypop.define import App
from lollypop.helper_signals import SignalsHelper


class TracksWidget(Gtk.ListBox, SignalsHelper):
    """
        A list of tracks
    """

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST,
                      None, (GObject.TYPE_PYOBJECT,))
    }

    signals = [
        (App().player, "queue-changed", "_on_queue_changed")
    ]

    def __init__(self):
        """
            Init track widget
        """
        Gtk.ListBox.__init__(self)
        SignalsHelper.__init__(self)
        self.get_style_context().add_class("trackswidget")
        self.set_property("hexpand", True)
        self.set_property("selection-mode", Gtk.SelectionMode.NONE)

    def update_playing(self, track_id):
        """
            Update playing track
            @param track_id as int
        """
        for row in self.get_children():
            row.set_indicator()

    def update_duration(self, track_id):
        """
            Update duration for track id
            @param track_id as int
        """
        for row in self.get_children():
            if row.track.id == track_id:
                row.update_duration()

#######################
# PROTECTED           #
#######################
    def _on_queue_changed(self, unused):
        """
            Update all position labels
        """
        for row in self.get_children():
            row.update_number_label()

#######################
# PRIVATE             #
#######################
    def __on_activate(self, widget, row):
        """
            Play activated item
            @param widget as TracksWidget
            @param row as TrackRow
        """
        self.emit("activated", row.track)
