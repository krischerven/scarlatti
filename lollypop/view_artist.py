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

from lollypop.define import ViewType, MARGIN
from lollypop.view_albums_box import AlbumsBoxView
from lollypop.widgets_banner_artist import ArtistBannerWidget


class ArtistView(AlbumsBoxView):
    """
        Show artist albums
    """

    def __init__(self, genre_ids, artist_ids):
        """
            Init ArtistView
            @param genre_ids as [int]
            @param artist_ids as [int]
        """
        AlbumsBoxView.__init__(self,
                               genre_ids,
                               artist_ids,
                               ViewType.SCROLLED |
                               ViewType.OVERLAY |
                               ViewType.ALBUM)
        self.__banner = ArtistBannerWidget(genre_ids, artist_ids)
        self.__banner.show()
        self._box.get_style_context().add_class("padding")
        self.add_widget(self._box, self.__banner)

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"genre_ids": self._genre_ids, "artist_ids": self._artist_ids}

    @property
    def scroll_shift(self):
        """
            Add scroll shift on y axes
            @return int
        """
        return self.__banner.height + MARGIN
