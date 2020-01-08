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

from lollypop.define import App
from lollypop.helper_signals import SignalsHelper, signals_map


class ViewControllerType:
    RADIO = "radio"
    ALBUM = "album"


class ViewController(SignalsHelper):
    """
        Update view for registered signals
        Should be herited by a Gtk.Widget
    """

    @signals_map
    def __init__(self, controller_type):
        """
            Init controller
            @param controller_type as ViewControllerType
        """
        return [
            (App().player, "current-changed", "_on_current_changed"),
            (App().player, "duration-changed", "_on_duration_changed"),
            (App().art, "%s-artwork-changed" % controller_type,
             "_on_artwork_changed")
        ]

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        pass

    def _on_artwork_changed(self, artwork, *args):
        pass

    def _on_duration_changed(self, player, track_id):
        pass

#######################
# PRIVATE             #
#######################
