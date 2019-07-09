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


class BannerWidget(Gtk.Overlay, SizeAllocationHelper):
    """
        Default banner widget
    """

    def __init__(self, view_type):
        """
            Init bannner
            @param view_type as ViewType
        """
        Gtk.Overlay.__init__(self)
        self._view_type = view_type
        self._collapsed = False
        self.set_property("valign", Gtk.Align.START)

    def init_background(self):
        """
            Init banner background
        """
        SizeAllocationHelper.__init__(self)
        self.get_style_context().add_class("black")
        self._artwork = Gtk.Image()
        self._artwork.get_style_context().add_class("black")
        self._artwork.show()
        self.add(self._artwork)

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        self._view_type = view_type

    def collapse(self, collapsed):
        """
            Collapse banner
            @param collapse as bool
        """
        self._collapsed = collapsed

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
        height = self.height
        return (height, height)

    @property
    def height(self):
        """
            Get wanted height
        """
        if self._collapsed:
            return ArtSize.SMALL + MARGIN * 2
        elif self._view_type & ViewType.SMALL:
            return ArtSize.LARGE + MARGIN * 2
        elif self._view_type & ViewType.MEDIUM:
            return ArtSize.BANNER + MARGIN * 2
        else:
            return ArtSize.BANNER + MARGIN * 2

#######################
# PROTECTED           #
#######################


#######################
# PRIVATE             #
#######################
