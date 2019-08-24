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

from lollypop.define import App, ArtSize, ArtBehaviour, MARGIN
from lollypop.widgets_banner import BannerWidget


class PlaylistsBannerWidget(BannerWidget):
    """
        Banner for playlists
    """

    def __init__(self, view_type):
        """
            Init banner
            @param view_type as ViewType
        """
        BannerWidget.__init__(self, view_type)
        grid = Gtk.Grid()
        grid.set_property("valign", Gtk.Align.CENTER)
        grid.show()
        new_button = Gtk.Button.new_with_label(_("New playlist"))
        new_button.connect("clicked", self.__on_new_button_clicked)
        new_button.set_property("halign", Gtk.Align.CENTER)
        new_button.get_style_context().add_class("menu-button-48")
        new_button.get_style_context().add_class("black-transparent")
        new_button.get_style_context().add_class("bold")
        new_button.set_hexpand(True)
        new_button.show()
        grid.add(new_button)
        self.add_overlay(grid)

#######################
# PROTECTED           #
#######################
    def _handle_size_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_size_allocate(self, allocation):
            App().art_helper.set_banner_artwork(
                # +100 to prevent resize lag
                allocation.width + 100,
                ArtSize.BANNER + MARGIN * 2,
                self._artwork.get_scale_factor(),
                ArtBehaviour.BLUR |
                ArtBehaviour.DARKER,
                self.__on_artwork)

#######################
# PRIVATE             #
#######################
    def __on_new_button_clicked(self, button):
        """
            Add a new playlist
            @param button as Gtk.Button
        """
        App().playlists.add(App().playlists.get_new_name())

    def __on_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is not None:
            self._artwork.set_from_surface(surface)
