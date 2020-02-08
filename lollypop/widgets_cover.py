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

from gi.repository import Gtk, GLib

from lollypop.define import App, ArtSize, ArtBehaviour, ViewType, Type
from lollypop.utils import set_cursor_type, popup_widget
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.helper_gestures import GesturesHelper


class CoverWidget(Gtk.EventBox, SignalsHelper, GesturesHelper):
    """
        Widget showing current album cover
    """

    @signals_map
    def __init__(self, album, view_type=ViewType.DEFAULT):
        """
            Init cover widget
            @param view_type as ViewType
        """
        Gtk.EventBox.__init__(self)
        GesturesHelper.__init__(self, self)
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self.__album = album
        self.__view_type = view_type
        self.__image_button = None
        self.__art_size = 1
        self.__artwork = Gtk.Image.new()
        self.__artwork.show()
        self.add(self.__artwork)
        self.connect("realize", set_cursor_type)
        return [
            (App().art, "album-artwork-changed", "_on_album_artwork_changed")
        ]

    def set_art_size(self, art_size):
        """
            Set cover artwork size
            @param art_size as int
        """
        if self.__art_size == art_size:
            return
        self.__art_size = art_size
        App().art_helper.set_frame(self.__artwork,
                                   "small-cover-frame",
                                   self.__art_size,
                                   self.__art_size)
        App().art_helper.set_album_artwork(
                self.__album,
                self.__art_size,
                self.__art_size,
                self.__artwork.get_scale_factor(),
                ArtBehaviour.CACHE | ArtBehaviour.CROP_SQUARE,
                self.__on_album_artwork)

#######################
# PROTECTED           #
#######################
    def _on_album_artwork_changed(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album_id as int
        """
        if self.__album is None:
            return
        if album_id == self.__album.id:
            App().art_helper.set_album_artwork(
                self.__album,
                self.__art_size,
                self.__art_size,
                self.__artwork.get_scale_factor(),
                ArtBehaviour.CACHE | ArtBehaviour.CROP_SQUARE,
                self.__on_album_artwork)

    def _on_primary_press_gesture(self, x, y, event):
        """
            Show covers popover
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        if self.__view_type & ViewType.ALBUM:
            from lollypop.widgets_artwork_album import AlbumArtworkSearchWidget
            artwork_search = AlbumArtworkSearchWidget(self.__album,
                                                      self.__view_type)
            artwork_search.show()
            # Let current animation run
            GLib.timeout_add(250, artwork_search.populate)
            popup_widget(artwork_search, self)
        else:
            App().window.container.show_view([Type.ALBUM], self.__album)

#######################
# PRIVATE             #
#######################
    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is None:
            if self.__art_size == ArtSize.BANNER:
                icon_size = Gtk.IconSize.DIALOG
            else:
                icon_size = Gtk.IconSize.DND
            self.__artwork.set_from_icon_name("folder-music-symbolic",
                                              icon_size)
        else:
            self.__artwork.set_from_surface(surface)
            del surface
