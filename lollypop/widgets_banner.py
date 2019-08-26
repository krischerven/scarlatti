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

from lollypop.define import ArtSize, ViewType, MARGIN
from lollypop.helper_size_allocation import SizeAllocationHelper


class Overlay(Gtk.Overlay):
    """
        Overlay with constraint size
    """
    def __init__(self, banner):
        """
            Init overlay
            @param banner as BannerWidget
        """
        Gtk.Overlay.__init__(self)
        self.__banner = banner

    def do_get_preferred_width(self):
        """
            Force preferred width
        """
        (min, nat) = Gtk.Bin.do_get_preferred_width(self)
        # Allow resizing
        return (0, 0)

    def do_get_preferred_height(self):
        """
           Force preferred height
        """
        height = self.__banner.height
        return (height, height)


class BannerWidget(Gtk.Revealer, SizeAllocationHelper):
    """
        Default banner widget
    """

    def __init__(self, view_type):
        """
            Init bannner
            @param view_type as ViewType
        """
        Gtk.Revealer.__init__(self)
        SizeAllocationHelper.__init__(self)
        self._view_type = view_type
        self.set_property("valign", Gtk.Align.START)
        self.get_style_context().add_class("black")
        self.__overlay = Overlay(self)
        self.__overlay.show()
        self._artwork = Gtk.Image()
        self._artwork.show()
        self._artwork.get_style_context().add_class("black")
        self._artwork.set_opacity(0.98)
        self.__overlay.add(self._artwork)
        self.add(self.__overlay)
        self.set_reveal_child(True)
        self.set_transition_duration(250)

    def add_overlay(self, widget):
        """
            Add widget to overlay
            @param widget as Gtk.Widget
        """
        self.__overlay.add_overlay(widget)

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        self._view_type = view_type

    @property
    def height(self):
        """
            Get wanted height
            @return int
        """
        if self._view_type & (ViewType.MEDIUM | ViewType.SMALL):
            return ArtSize.MEDIUM + MARGIN * 2
        else:
            return ArtSize.BANNER + MARGIN * 2
