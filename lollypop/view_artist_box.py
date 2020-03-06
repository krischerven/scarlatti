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
        self.__banner = ArtistBannerWidget(genre_ids,
                                           artist_ids,
                                           self._storage_type,
                                           view_type)
        self.__banner.show()
        self._box.get_style_context().add_class("padding")
        self.add_widget(self._box, self.__banner)

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
            Add scroll shift on y axes
            @return int
        """
        return self.__banner.height + MARGIN
