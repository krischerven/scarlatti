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

from gi.repository import Gtk, GLib

from gettext import gettext as _

from lollypop.define import App, Type
from lollypop.utils import on_realize
from lollypop.helper_overlay import OverlayHelper


class OverlayDecadeHelper(OverlayHelper):
    """
        An overlay helper for decade
    """

    def __init__(self):
        """
            Init helper
        """
        OverlayHelper.__init__(self)

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, show_overlay):
        """
            Set overlay
            @param show_overlay as bool
        """
        if self._lock_overlay or self._show_overlay == show_overlay:
            return
        OverlayHelper._show_overlay_func(self, show_overlay)
        if show_overlay:
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
            self.__play_button.connect("clicked", self.__on_play_clicked)
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
    def __on_play_clicked(self, button):
        """
            Play decade
            @param button as Gtk.Button
        """
        if App().player.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        App().player.play_albums_for_filter_for_filter(
            None, [Type.YEARS], self._data)
        return True
