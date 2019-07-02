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

from gi.repository import GLib

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type
from locale import strcoll
from lollypop.widgets_artist_rounded import RoundedArtistWidget
from lollypop.utils import get_icon_name


class RoundedArtistsView(FlowBoxView):
    """
        Show artists in a FlowBox
    """

    def __init__(self, view_type, destroy=True):
        """
            Init artist view
            @param view_type as ViewType
            @param destroy as bool
        """
        FlowBoxView.__init__(self)
        self.__view_type = view_type
        self.__destroy = destroy
        self._widget_class = RoundedArtistWidget
        self.connect("destroy", self.__on_destroy)
        self._empty_icon_name = get_icon_name(Type.ARTISTS)

    def add_value(self, item):
        """
            Insert item
            @param item as (int, str, str)
        """
        for child in self._box.get_children():
            if child.data == item[0]:
                return
        # Setup sort on insert
        self._box.set_sort_func(self.__sort_func)
        widget = RoundedArtistWidget(item, self.__view_type, self.font_height)
        widget.populate()
        widget.show()
        self._box.insert(widget, -1)

    def remove_value(self, item_id):
        """
            Remove value
            @param item_id as int
        """
        for child in self._box.get_children():
            if child.data == item_id:
                child.destroy()
                break

    def make_destroyable(self):
        """
            Mark view as destroyable
        """
        self.__destroy = True

    @property
    def should_destroy(self):
        return self.__destroy

#######################
# PROTECTED           #
#######################
    def _add_items(self, items, *args):
        """
            Add artists to the view
            @param items as [(int, str, str)]
        """
        FlowBoxView._add_items(self, items, self.__view_type)

    def _on_item_activated(self, flowbox, widget):
        """
            Show artist albums
            @param flowbox as Gtk.Flowbox
            @param widget as ArtistRoundedWidget
        """
        App().window.emit("show-can-go-back", True)
        App().window.emit("can-go-back-changed", True)
        App().window.container.show_view([Type.ARTISTS], [widget.data])

    def _on_map(self, widget):
        """
            Set active ids
        """
        FlowBoxView._on_map(self, widget)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", [Type.ARTISTS]))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", []))
        App().settings.set_value("state-three-ids",
                                 GLib.Variant("ai", []))
        self.__art_signal_id = App().art.connect(
                                              "artist-artwork-changed",
                                              self.__on_artist_artwork_changed)

    def _on_unmap(self, widget):
        """
            Connect signals
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)

#######################
# PRIVATE             #
#######################
    def __sort_func(self, widget1, widget2):
        """
            Sort function
            @param widget1 as RoundedArtistWidget
            @param widget2 as RoundedArtistWidget
        """
        # Static vs static
        if widget1.data < 0 and widget2.data < 0:
            return widget1.data < widget2.data
        # Static entries always on top
        elif widget2.data < 0:
            return True
        # Static entries always on top
        if widget1.data < 0:
            return False
        # String comparaison for non static
        else:
            return strcoll(widget1.sortname, widget2.sortname)

    def __on_destroy(self, widget):
        """
            Stop loading
            @param widget as Gtk.Widget
        """
        RoundedArtistsView.stop(self)

    def __on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        for child in self._box.get_children():
            if child.name == prefix:
                child.set_artwork()
