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
from lollypop.helper_signals import SignalsHelper, signals_map


class ToolbarTitle(Gtk.Bin, SignalsHelper):
    """
        Title toolbar
    """

    @signals_map
    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        self.__progress_widget = ProgressPlayerWidget()
        self.add(self.__progress_widget)
        return [
            (App().player, "status-changed", "_on_status_changed")
        ]

    def set_width(self, width):
        """
            Set Gtk.Scale progress width
            @param width as int
        """
        self.set_property("width_request", width)

#######################
# PROTECTED           #
#######################
    def _on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        if player.is_playing:
            self.__progress_widget.show()
        else:
            self.__progress_widget.hide()
