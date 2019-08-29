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

from gi.repository import Gtk

from lollypop.define import App
from lollypop.widgets_player_progress import ProgressPlayerWidget


class ToolbarTitle(Gtk.Bin):
    """
        Title toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        progress_widget = ProgressPlayerWidget()
        progress_widget.show()
        self.add(progress_widget)

    def set_width(self, width):
        """
            Set Gtk.Scale progress width
            @param width as int
        """
        self.set_property("width_request", width)

    def set_mini(self, mini):
        """
            Show/hide
            @param mini as bool
        """
        if mini:
            self.hide()
        elif App().player.current_track.id is not None:
            self.show()
