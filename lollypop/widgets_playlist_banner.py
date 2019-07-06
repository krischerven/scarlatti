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

from random import choice

from lollypop.objects import Track
from lollypop.define import App, ArtSize, ArtBehaviour
from lollypop.helper_size_allocation import SizeAllocationHelper


class PlaylistBannerWidget(Gtk.Overlay, SizeAllocationHelper):
    """
        Banner for playlist
    """

    def __init__(self, playlist_id):
        """
            Init artist banner
            @param playlist_id as int
        """
        Gtk.Overlay.__init__(self)
        SizeAllocationHelper.__init__(self)
        self.__track = None
        self.__track_ids = []
        if App().playlists.get_smart(playlist_id):
            request = App().playlists.get_smart_sql(playlist_id)
            if request is not None:
                self.__track_ids = App().db.execute(request)
        else:
            self.__track_ids = App().playlists.get_track_ids(playlist_id)
        self.__height = self.default_height
        self.__playlist_id = playlist_id
        self.set_property("valign", Gtk.Align.START)
        self.get_style_context().add_class("black")
        self.__artwork = Gtk.Image()
        self.__artwork.get_style_context().add_class("black")
        self.__artwork.show()
        self.add(self.__artwork)

    def set_height(self, height):
        """
            Set height
            @param height as int
        """
        self.__height = height

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
        return (self.__height, self.__height)

    @property
    def height(self):
        """
            Get height
            @return int
        """
        return self.__height

    @property
    def default_height(self):
        """
            Get default height
        """
        if App().window.is_adaptive:
            return ArtSize.LARGE
        else:
            return ArtSize.BANNER

#######################
# PROTECTED           #
#######################
    def _handle_size_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if SizeAllocationHelper._handle_size_allocate(self, allocation):
            if self.__track_ids and self.__track is None:
                track_id = choice(self.__track_ids)
                self.__track_ids.remove(track_id)
                self.__track = Track(track_id)
            if self.__track is not None:
                App().art_helper.set_album_artwork(
                    self.__track.album,
                    # +100 to prevent resize lag
                    allocation.width + 100,
                    allocation.height,
                    self.__artwork.get_scale_factor(),
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
            self.__artwork.set_from_surface(surface)
