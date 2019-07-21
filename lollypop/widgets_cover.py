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

from gi.repository import Gtk, GObject

from gettext import gettext as _

from lollypop.define import App, ArtSize, ArtBehaviour, ViewType
from lollypop.helper_overlay_album import OverlayAlbumHelper
from lollypop.utils import on_realize


class CoverWidget(Gtk.EventBox, OverlayAlbumHelper):
    """
        Widget showing current album cover
    """
    __gsignals__ = {
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album, view_type=ViewType.DEFAULT):
        """
            Init cover widget
            @param view_type as ViewType
        """
        Gtk.EventBox.__init__(self)
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self._album = album
        self.__image_button = None
        self._artwork = Gtk.Image.new()
        self._artwork.show()
        self._artwork.get_style_context().add_class("white")
        self._overlay = Gtk.Overlay.new()
        self._overlay.show()
        OverlayAlbumHelper.__init__(self, view_type)
        self._overlay.add(self._artwork)
        self.add(self._overlay)
        self.connect("enter-notify-event",
                     lambda x, y: self.show_overlay(True))
        self.connect("leave-notify-event",
                     lambda x, y: self.show_overlay(False))
        self.connect("destroy", self.__on_destroy)
        self.__art_signal_id = App().art.connect(
                                              "album-artwork-changed",
                                              self.__on_album_artwork_changed)

    def set_artwork(self, art_size):
        """
            Set cover artwork
            @param art_size as int
        """
        self.__art_size = art_size
        App().art_helper.set_frame(self._artwork,
                                   "small-cover-frame",
                                   self.__art_size,
                                   self.__art_size)
        App().art_helper.set_album_artwork(
                self._album,
                self.__art_size,
                self.__art_size,
                self._artwork.get_scale_factor(),
                ArtBehaviour.CACHE | ArtBehaviour.CROP_SQUARE,
                self.__on_album_artwork)

    def show_overlay(self, show):
        """
            Set overlay
            @param show as bool
        """
        if (show and self._big_grid is not None) or\
                (not show and self._big_grid is None):
            return
        OverlayAlbumHelper.show_overlay(self, show)
        if show:
            # Image button
            self.__image_button = Gtk.Button.new_from_icon_name(
                "image-x-generic-symbolic",
                Gtk.IconSize.INVALID)
            self.__image_button.set_property("has-tooltip", True)
            self.__image_button.set_tooltip_text(_("Change artwork"))
            self.__image_button.connect("realize", on_realize)
            self.__image_button.connect("clicked", self.__on_artwork_clicked)
            self.__image_button.get_image().set_pixel_size(self._pixel_size)
            self.__image_button.show()
            self._small_grid.add(self.__image_button)
            self.__image_button.get_style_context().add_class(
                "overlay-button")
        else:
            self.__image_button.destroy()
            self.__image_button = None

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)

    def __on_album_artwork_changed(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album_id as int
        """
        if self._album is None:
            return
        if album_id == self._album.id:
            App().art_helper.set_album_artwork(
                self._album,
                self.__art_size,
                self.__art_size,
                self._artwork.get_scale_factor(),
                ArtBehaviour.CACHE | ArtBehaviour.CROP_SQUARE,
                self.__on_album_artwork)

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
            self._artwork.set_from_icon_name("folder-music-symbolic",
                                             icon_size)
        else:
            self._artwork.set_from_surface(surface)

    def __on_artwork_clicked(self, button):
        """
            Popover with album art downloaded from the web (in fact google :-/)
            @param button as Gtk.Button
        """
        from lollypop.pop_artwork import CoversPopover
        popover = CoversPopover(self._album)
        popover.set_relative_to(button)
        popover.popup()
        return True
