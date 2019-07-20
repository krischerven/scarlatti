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

from gettext import gettext as _

from lollypop.utils import on_realize
from lollypop.helper_overlay import OverlayHelper


class OverlayGenreHelper(OverlayHelper):
    """
        An overlay helper for a genre
    """

    def __init__(self):
        """
            Init helper
        """
        OverlayHelper.__init__(self)

    def show_overlay(self, show):
        """
            Set overlay
            @param show as bool
        """
        if (show and self._big_grid is not None) or\
                (not show and self._big_grid is None):
            return
        OverlayHelper.show_overlay(self, show)
        if show:
            # Play button
            self.__play_button = Gtk.Button.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.INVALID)
            self.__play_button.set_tooltip_text(_("Play"))
            self.__play_button.get_image().set_pixel_size(self._pixel_size +
                                                          20)
            self.__play_button.set_property("has-tooltip", True)
            self._big_grid.set_margin_bottom(10)
            self._big_grid.set_margin_start(10)
            self.__play_button.connect("realize", on_realize)
            self.__play_button.connect("clicked", self._on_play_clicked)
            self.__play_button.show()
            self._big_grid.add(self.__play_button)
            self.__play_button.get_style_context().add_class(
                "overlay-button-rounded")
        else:
            self.__play_button.destroy()
            self.__play_button = None

#######################
# PRIVATE             #
#######################
    def _on_play_clicked(self, button):
        pass
