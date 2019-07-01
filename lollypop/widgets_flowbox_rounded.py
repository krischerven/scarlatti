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

from gi.repository import GLib, Gtk, Pango, GObject

from lollypop.define import ArtSize, ViewType
from lollypop.utils import on_query_tooltip, on_realize


class RoundedFlowBoxWidget(Gtk.FlowBoxChild):
    """
        Rounded flowbox child widget
    """

    __gsignals__ = {
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, data, name, sortname, view_type):
        """
            Init widget
            @param data as object
            @param name as str
            @param sortname as str
            @param view_type as ViewType
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self._artwork = None
        self._data = data
        self.__name = name
        self.__sortname = sortname
        self.__filtered = False
        self.set_view_type(view_type)
        self._scale_factor = self.get_scale_factor()
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self.connect("realize", on_realize)

    def populate(self):
        """
            Populate widget content
        """
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__label = Gtk.Label.new()
        self.__label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__label.set_property("halign", Gtk.Align.CENTER)
        self.__label.set_property("has-tooltip", True)
        self.__label.connect("query-tooltip", on_query_tooltip)
        self.__label.set_markup(
            "<b>" + GLib.markup_escape_text(self.__name) + "</b>")
        self._artwork = Gtk.Image.new()
        self._artwork.set_size_request(self._art_size, self._art_size)
        self._artwork.show()
        self.set_artwork()
        self._overlay = Gtk.Overlay()
        self._overlay.add(self._artwork)
        grid.add(self._overlay)
        grid.add(self.__label)
        self._widget = Gtk.EventBox()
        self._widget.set_property("has-tooltip", True)
        self._widget.add(grid)
        self.add(self._widget)
        self.show_all()

    def set_view_type(self, view_type):
        """
            Update view type
            @param view_type as ViewType
        """
        self.__view_type = view_type
        if self.__view_type & ViewType.SMALL:
            self._art_size = ArtSize.LARGE
        elif self.__view_type & ViewType.MEDIUM:
            self._art_size = ArtSize.BANNER
        else:
            self._art_size = ArtSize.BIG

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    def rename(self, name):
        """
            Rename widget
            @param name as str
        """
        self.__label.set_markup("<b>" + GLib.markup_escape_text(name) + "</b>")

    def set_filtered(self, b):
        """
            Set widget filtered
            @param b as bool
            @return bool (should be shown)
        """
        self.__filtered = b
        return not b

    def disable_artwork(self):
        """
            Disable widget artwork
        """
        if self._artwork is not None:
            self._artwork.set_size_request(self._art_size, self._art_size)
            self._artwork.set_from_surface(None)

    def set_artwork(self):
        """
            Set widget artwork
        """
        if self._artwork is not None:
            self._artwork.set_size_request(self._art_size, self._art_size)

    @property
    def name(self):
        """
            Get name
            @return str
        """
        return self.__name

    @property
    def sortname(self):
        """
            Get sortname
            @return str
        """
        return self.__sortname

    @property
    def data(self):
        """
            Get associated data
            @return object
        """
        return self._data

    @property
    def filter(self):
        """
            Current filter
            @return str
        """
        return self.name.lower()

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__filtered

    @property
    def is_populated(self):
        """
            True if album populated
        """
        return True

#######################
# PROTECTED           #
#######################

    def _get_album_ids(self):
        return []

#######################
# PRIVATE             #
#######################
