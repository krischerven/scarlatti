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

from gi.repository import Gdk

from random import shuffle

from lollypop.objects_album import Album
from lollypop.define import App, ArtSize, ArtBehaviour, ViewType, MARGIN
from lollypop.widgets_banner import BannerWidget


class ArtistBannerWidget(BannerWidget):
    """
        Banner for artist
    """

    def __init__(self, artist_id, view_type=ViewType.DEFAULT):
        """
            Init artist banner
            @param artist_id as int
            @param view_type as ViewType (Unused)
        """
        BannerWidget.__init__(self, view_type)
        self.__album_ids = None
        self.__album_id = None
        self.__artist_id = artist_id
        self.connect("destroy", self.__on_destroy)
        self.__art_signal_id = App().art.connect(
                                           "artist-artwork-changed",
                                           self.__on_artist_artwork_changed)

#######################
# PROTECTED           #
#######################
    def _handle_size_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_size_allocate(self, allocation):
            if App().settings.get_value("artist-artwork"):
                artist = App().artists.get_name(self.__artist_id)
                App().art_helper.set_artist_artwork(
                                            artist,
                                            # +100 to prevent resize lag
                                            allocation.width + 100,
                                            ArtSize.BANNER + MARGIN * 2,
                                            self.get_scale_factor(),
                                            ArtBehaviour.BLUR_HARD |
                                            ArtBehaviour.DARKER,
                                            self.__on_artist_artwork)
            else:
                self.__use_album_artwork(allocation.width,
                                         ArtSize.BANNER + MARGIN * 2)

#######################
# PRIVATE             #
#######################
    def __use_album_artwork(self, width, height):
        """
            Set artwork with album artwork
            @param width as int
            @param height as int
        """
        # Select an album
        if self.__album_id is None:
            if self.__album_ids is None:
                if App().settings.get_value("show-performers"):
                    self.__album_ids = App().tracks.get_album_ids(
                        [self.__artist_id], [])
                else:
                    self.__album_ids = App().albums.get_ids(
                        [self.__artist_id], [])
                shuffle(self.__album_ids)
            if self.__album_ids:
                self.__album_id = self.__album_ids.pop(0)
        # Get artwork
        if self.__album_id is not None:
            album = Album(self.__album_id)
            App().art_helper.set_album_artwork(
                album,
                # +100 to prevent resize lag
                width + 100,
                height,
                self._artwork.get_scale_factor(),
                ArtBehaviour.BLUR_HARD |
                ArtBehaviour.DARKER,
                self.__on_album_artwork)

    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)

    def __on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        artist = App().artists.get_name(self.__artist_id)
        if prefix == artist:
            rect = Gdk.Rectangle()
            rect.width = self.get_allocated_width()
            rect.height = self.get_allocated_height()
            self.__width = 0
            self.__handle_size_allocate(rect)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is None:
            self.__album_id = None
            self.__use_album_artwork(self.get_allocated_width(),
                                     self.get_allocated_height())
        else:
            self._artwork.set_from_surface(surface)

    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as str
        """
        if surface is None:
            self.__use_album_artwork(self.get_allocated_width(),
                                     self.get_allocated_height())
        else:
            self._artwork.set_from_surface(surface)
