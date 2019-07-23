# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk

from lollypop.view_tracks import TracksView
from lollypop.define import App, ViewType, MARGIN
from lollypop.widgets_utils import Popover


class TracksPopover(Popover, TracksView):
    """
        A popover with tracks
    """

    def __init__(self, album):
        """
            Init popover
            @param album as Album
            @param width as int
        """
        Popover.__init__(self)
        TracksView.__init__(self, ViewType.TWO_COLUMNS)
        self._album = album
        self.get_style_context().add_class("box-shadow")
        view_height = self.requested_height[0]
        window_width = App().window.get_allocated_width()
        window_height = App().window.get_allocated_height()
        wanted_width = min(900, window_width * 0.5)
        wanted_height = max(200,
                            min(window_height * 0.4, view_height + MARGIN))
        self.populate()
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self._responsive_widget)
        scrolled.set_property("width-request", wanted_width)
        scrolled.set_property("height-request", wanted_height)
        scrolled.show()
        self._responsive_widget.set_property("valign", Gtk.Align.CENTER)
        self._responsive_widget.show()
        self.add(scrolled)

#######################
# PROTECTED           #
#######################
    def _on_tracks_populated(self, disc_number):
        """
            Tracks populated
            @param disc_number
        """
        if not self.is_populated:
            self.populate()
