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

from lollypop.define import ViewType, MARGIN, App
from lollypop.widgets_banner_artist import ArtistBannerWidget
from lollypop.view_album import AlbumView
from lollypop.objects_album import Album
from lollypop.view_lazyloading import LazyLoadingView


class ArtistViewList(LazyLoadingView):
    """
        Show artist albums in a list with tracks
    """

    def __init__(self, genre_ids, artist_ids, storage_type):
        """
            Init ArtistView
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param storage_type as StorageType
        """
        LazyLoadingView.__init__(self, storage_type,
                                 ViewType.SCROLLED |
                                 ViewType.OVERLAY |
                                 ViewType.ARTIST)
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self.__storage_type = storage_type
        self.__banner = ArtistBannerWidget(genre_ids, artist_ids, storage_type)
        self.__banner.show()
        self.__list = Gtk.Box.new(Gtk.Orientation.VERTICAL, MARGIN * 4)
        self.__list.show()
        self.add_widget(self.__list, self.__banner)

    def populate(self):
        """
            Populate list
        """
        album_ids = App().albums.get_ids(self.__artist_ids,
                                         self.__genre_ids,
                                         self.storage_type)
        LazyLoadingView.populate(self, album_ids)

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"genre_ids": self.__genre_ids,
                "artist_ids": self.__artist_ids,
                "storage_type": self.storage_type}

    @property
    def scroll_shift(self):
        """
            Add scroll shift on y axes
            @return int
        """
        return self.__banner.height + MARGIN

#######################
# PROTECTED           #
#######################
    def _get_child(self, album_id):
        """
            Get an album view widget
            @param album_id as int
            @return AlbumView
        """
        if self.destroyed:
            return None
        widget = AlbumView(Album(album_id),
                           self.storage_type,
                           ViewType.DEFAULT)
        widget.show()
        widget.set_property("valign", Gtk.Align.START)
        self.__list.add(widget)
        return widget
