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

from gi.repository import GObject, Pango

from lollypop.define import ViewType
from lollypop.widgets_row import Row
from lollypop.widgets_row_dnd import DNDRow


class TrackRow(Row, DNDRow):
    """
        A track row
    """

    __gsignals__ = {
        "insert-track": (
            GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "remove-track": (
            GObject.SignalFlags.RUN_FIRST, None, ()),
        "insert-album": (
            GObject.SignalFlags.RUN_FIRST, None, (
                int, GObject.TYPE_PYOBJECT, bool)),
        "do-selection": (
            GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def get_best_height(widget):
        """
            Calculate widget height
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(layout.get_pixel_size()[1])
        # application.css
        min_height = 32
        if font_height > min_height:
            height = font_height
        else:
            height = min_height
        return height

    def __init__(self, track, album_artist_ids, view_type):
        """
            Init row widget and show it
            @param track as Track
            @pram album_artist_ids as [int]
            @param view_type as ViewType
        """
        Row.__init__(self, track, album_artist_ids, view_type)
        self._grid.insert_column(0)
        self._grid.attach(self._indicator, 0, 0, 1, 1)
        self.show_all()
        if view_type & ViewType.DND:
            DNDRow.__init__(self)

#######################
# PROTECTED           #
#######################
    def _check_track(self):
        """
            Check track always valid, destroy if not
        """
        if self._track not in self._track.album.tracks:
            self.destroy()

#######################
# PRIVATE             #
#######################
