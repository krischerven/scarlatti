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

from lollypop.define import App
from lollypop.objects import Track
from lollypop.utils import on_realize
from lollypop.helper_overlay import OverlayHelper


class OverlayRadioHelper(OverlayHelper):
    """
        An overlay helper for a radio
    """

    def __init__(self, radios):
        """
            Init helper
            @param radios as Radios
        """
        OverlayHelper.__init__(self)
        self.__radios = radios

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, show_overlay):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or self._show_overlay == show_overlay:
            return
        OverlayHelper._show_overlay_func(self, show_overlay)
        if show_overlay:
            # Play button
            self.__play_button = Gtk.Button.new_from_icon_name(
                "media-playback-start-symbolic",
                Gtk.IconSize.INVALID)
            self.__play_button.get_image().set_pixel_size(self._pixel_size +
                                                          20)
            self.__play_button.set_property("has-tooltip", True)
            self.__play_button.set_tooltip_text(_("Play"))
            self.__play_button.connect("realize", on_realize)
            self.__play_button.connect("clicked", self.__on_play_clicked)
            self.__play_button.show()
            self._big_grid.add(self.__play_button)
            self.__play_button.get_style_context().add_class(
                "overlay-button-rounded")
            # Edit button
            self.__artwork_button = Gtk.Button.new_from_icon_name(
                "document-properties-symbolic",
                Gtk.IconSize.INVALID)
            self.__artwork_button.get_image().set_pixel_size(self._pixel_size)
            self.__artwork_button.set_property("has-tooltip", True)
            self.__artwork_button.set_tooltip_text(_("Modify radio"))
            self.__artwork_button.connect("realize", on_realize)
            self.__artwork_button.connect("clicked", self.__on_edit_clicked)
            self.__artwork_button.show()
            self._small_grid.add(self.__artwork_button)
            self.__artwork_button.get_style_context().add_class(
                "overlay-button")
        else:
            self.__play_button.destroy()
            self.__play_button = None
            self.__artwork_button.destroy()
            self.__artwork_button = None

#######################
# PRIVATE             #
#######################
    def __on_play_clicked(self, button):
        """
            Play radio
            @param button as Gtk.Button
        """
        track = Track()
        track.set_radio_id(self._radio_id)
        App().player.load(track)

    def __on_edit_clicked(self, button):
        """
            Edit radio
            @param button as Gtk.Button
        """
        from lollypop.pop_radio import RadioPopover
        popover = RadioPopover(self._radio_id, self.__radios)
        popover.set_relative_to(button)
        popover.connect("closed", self._on_popover_closed)
        self._lock_overlay = True
        popover.popup()
