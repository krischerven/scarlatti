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


from random import choice

from lollypop.objects_track import Track
from lollypop.define import App, ArtSize, ArtBehaviour, MARGIN
from lollypop.widgets_banner import BannerWidget


class PlaylistBannerWidget(BannerWidget):
    """
        Banner for playlist
    """

    def __init__(self, playlist_id, view_type):
        """
            Init artist banner
            @param playlist_id as int
            @param view_type as ViewType
        """
        BannerWidget.__init__(self, view_type)
        self.__track = None
        self.__track_ids = []
        if App().playlists.get_smart(playlist_id):
            request = App().playlists.get_smart_sql(playlist_id)
            if request is not None:
                self.__track_ids = App().db.execute(request)
        else:
            self.__track_ids = App().playlists.get_track_ids(playlist_id)
        self.__playlist_id = playlist_id

#######################
# PROTECTED           #
#######################
    def _handle_size_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_size_allocate(self, allocation):
            if self.__track_ids and self.__track is None:
                track_id = choice(self.__track_ids)
                self.__track_ids.remove(track_id)
                self.__track = Track(track_id)
            if self.__track is not None:
                App().art_helper.set_album_artwork(
                    self.__track.album,
                    # +100 to prevent resize lag
                    allocation.width + 100,
                    ArtSize.BANNER + MARGIN * 2,
                    self._artwork.get_scale_factor(),
                    ArtBehaviour.BLUR_HARD |
                    ArtBehaviour.DARKER,
                    self.__on_album_artwork)

#######################
# PRIVATE             #
#######################
    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is not None:
            self._artwork.set_from_surface(surface)
