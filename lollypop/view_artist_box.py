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

from gi.repository import Gtk

from lollypop.define import ViewType, MARGIN
from lollypop.view_albums_box import AlbumsBoxView
from lollypop.widgets_banner_artist import ArtistBannerWidget


class ArtistViewBox(AlbumsBoxView):
    """
        Show artist albums in a box
    """

    def __init__(self, genre_ids, artist_ids, storage_type, view_type):
        """
            Init ArtistView
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param storage_type as StorageType
            @param view_type as ViewType
        """
        AlbumsBoxView.__init__(self,
                               genre_ids,
                               artist_ids,
                               storage_type,
                               view_type |
                               ViewType.OVERLAY |
                               ViewType.ARTIST)
        self.__others_boxes = []
        self.__banner = ArtistBannerWidget(genre_ids,
                                           artist_ids,
                                           self._storage_type,
                                           view_type)
        self.__banner.show()
        self._box.get_style_context().add_class("padding")
        self.connect("populated", self.__on_populated)
        self.__grid = Gtk.Grid()
        self.__grid.show()
        self.__grid.set_property("valign", Gtk.Align.START)
        self.__grid.set_row_spacing(10)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.add(self._box)
        self.add_widget(self.__grid, self.__banner)

    @property
    def filtered(self):
        """
            Get filtered children
            @return [Gtk.Widget]
        """
        filtered = self.children
        for box in self.__others_boxes:
            for child in box.children:
                filtered.append(child)
        return filtered

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"genre_ids": self._genre_ids,
                "artist_ids": self._artist_ids,
                "storage_type": self.storage_type,
                "view_type": self.view_type}

    @property
    def scroll_shift(self):
        """
            Get scroll shift for y axes
            @return int
        """
        return self.__banner.height + MARGIN

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Set initial view state
            @param widget as GtK.Widget
        """
        AlbumsBoxView._on_map(self, widget)
        if self.view_type & ViewType.SCROLLED:
            self.scrolled.grab_focus()

#######################
# PRIVATE             #
#######################
    def __on_populated(self, view):
        """
            Add appears on albums
            @param view as ArtistViewBox
        """
        album_ids = []
        for child in self.children:
            album_ids.append(child.data.id)
        from lollypop.view_albums_line import AlbumsArtistAppearsOnLineView
        others_box = AlbumsArtistAppearsOnLineView(self._artist_ids,
                                                   self._genre_ids,
                                                   self.storage_type,
                                                   ViewType.SMALL |
                                                   ViewType.SCROLLED)
        others_box.set_margin_start(MARGIN)
        others_box.set_margin_end(MARGIN)
        others_box.populate(album_ids)
        self.__grid.add(others_box)
        self.__others_boxes.append(others_box)
