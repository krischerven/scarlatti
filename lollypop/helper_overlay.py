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

from lollypop.define import ArtSize


class OverlayHelper:
    """
        An overlay helper
    """

    def __init__(self):
        """
            Init helper
        """
        self.__spinner = None
        self._big_grid = None
        self._small_grid = None
        self._watch_loading = False
        self.__timeout_id = None
        self._pixel_size = ArtSize.BIG / 9

    def show_spinner(self, status):
        """
            Show/hide spinner
            @param status as bool
        """
        if status:
            if self.__spinner is None:
                self.__spinner = Gtk.Spinner()
                self.__spinner.show()
                self.__spinner.start()
                style_context = self.__spinner.get_style_context()
                style_context.add_class("black-transparent")
                self._overlay.add_overlay(self.__spinner)
        else:
            if self.__spinner is not None:
                self.__spinner.destroy()
                self.__spinner = None

    def show_overlay(self, show):
        """
            Set overlay
            @param show as bool
        """
        if (show and self._big_grid is not None) or\
                (not show and self._big_grid is None):
            return
        if show:
            self._big_grid = Gtk.Grid()
            self._big_grid.set_property("halign", Gtk.Align.START)
            self._big_grid.set_property("valign", Gtk.Align.END)
            self._big_grid.set_margin_start(6)
            self._big_grid.set_margin_bottom(6)
            self._big_grid.show()
            self._overlay.add_overlay(self._big_grid)
            self._small_grid = Gtk.Grid()
            self._small_grid.set_margin_bottom(6)
            self._small_grid.set_margin_end(6)
            self._small_grid.set_property("halign", Gtk.Align.END)
            self._small_grid.set_property("valign", Gtk.Align.END)
            self._overlay.add_overlay(self._small_grid)
            self._small_grid.show()
            self._big_grid.get_style_context().add_class("rounded-icon")
            self._small_grid.get_style_context().add_class(
                    "squared-icon-small")
        else:
            self._big_grid.destroy()
            self._big_grid = None
            self._small_grid.destroy()
            self._small_grid = None
