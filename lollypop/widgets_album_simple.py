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

from gi.repository import GLib, Gtk, Pango, GObject

from lollypop.widgets_album import AlbumWidget
from lollypop.helper_overlay_album import OverlayAlbumHelper
from lollypop.define import App, ArtSize, Shuffle, ViewType, ArtBehaviour, Type
from lollypop.utils import on_query_tooltip, on_realize


class AlbumSimpleWidget(Gtk.FlowBoxChild, AlbumWidget, OverlayAlbumHelper):
    """
        Album widget showing cover, artist and title
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album, genre_ids, artist_ids, view_type, font_height):
        """
            Init simple album widget
            @param album as Album
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
            @parma font_height as int
        """
        self.__widget = None
        self.__font_height = font_height
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.set_view_type(view_type)
        AlbumWidget.__init__(self, album, genre_ids, artist_ids)

    def populate(self):
        """
            Populate widget content
        """
        if self._artwork is None:
            OverlayAlbumHelper.__init__(self, self.__view_type)
            self._watch_loading = self._album.mtime <= 0
            self.set_property("halign", Gtk.Align.CENTER)
            self.set_property("valign", Gtk.Align.CENTER)
            self.__widget = Gtk.EventBox()
            grid = Gtk.Grid()
            grid.set_orientation(Gtk.Orientation.VERTICAL)
            self.__label = Gtk.Label.new()
            self.__label.set_justify(Gtk.Justification.CENTER)
            self.__label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__label.set_property("halign", Gtk.Align.CENTER)
            self.__label.set_property("has-tooltip", True)
            self.__label.connect("query-tooltip", on_query_tooltip)
            album_name = GLib.markup_escape_text(self._album.name)
            if self.__view_type & ViewType.ALBUM:
                self.__label.set_markup("<span alpha='40000'>%s</span>" %
                                        album_name)
            else:
                artist_name = GLib.markup_escape_text(", ".join(
                                                      self._album.artists))
                self.__label.set_markup(
                    "<b>%s</b>\n<span alpha='40000'>%s</span>" % (album_name,
                                                                  artist_name))
            eventbox = Gtk.EventBox()
            eventbox.add(self.__label)
            eventbox.connect("realize", on_realize)
            eventbox.connect("button-press-event",
                             self.__on_artist_button_press)
            eventbox.show()
            self.__widget.add(grid)
            self._overlay = Gtk.Overlay.new()
            self._artwork = Gtk.Image.new()
            self._overlay.add(self._artwork)
            grid.add(self._overlay)
            grid.add(eventbox)
            self.set_artwork()
            self.set_selection()
            if not self.__view_type & ViewType.SMALL:
                self.__widget.connect("enter-notify-event",
                                      self._on_enter_notify)
                self.__widget.connect("leave-notify-event",
                                      self._on_leave_notify)
            self.__widget.connect("button-release-event",
                                  self._on_button_release)
            self.__widget.connect("realize", on_realize)
            self.connect("destroy", self.__on_destroy)
            self.add(self.__widget)
        else:
            self.set_artwork()

    def disable_artwork(self):
        """
            Disable widget artwork
        """
        if self._artwork is not None:
            self._artwork.set_size_request(self.__art_size, self.__art_size)
            self._artwork.set_from_surface(None)

    def set_artwork(self):
        """
            Set artwork
        """
        if self.__widget is None:
            return
        if self.__art_size < ArtSize.BIG:
            frame = "small-cover-frame"
        else:
            frame = "cover-frame"
        App().art_helper.set_frame(self._artwork,
                                   frame,
                                   self.__art_size,
                                   self.__art_size)
        App().art_helper.set_album_artwork(self._album,
                                           self.__art_size,
                                           self.__art_size,
                                           self._artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE |
                                           ArtBehaviour.CROP_SQUARE,
                                           self.__on_album_artwork)

    def set_view_type(self, view_type):
        """
            Update artwork size
            @param view_type as ViewType
        """
        self.__view_type = view_type
        if self.__view_type & ViewType.SMALL:
            self.__art_size = ArtSize.MEDIUM
        elif self.__view_type & ViewType.MEDIUM:
            self.__art_size = ArtSize.BANNER
        else:
            self.__art_size = ArtSize.BIG
        self.set_size_request(self.__art_size,
                              self.__art_size + self.__font_height * 2)

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self.__widget is None:
            return (0, 0)
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    @property
    def name(self):
        """
            Get name
            @return str
        """
        return self.__label.get_text()

    @property
    def artwork(self):
        """
            Get album artwork
            @return Gtk.Image
        """
        return self._artwork

    @property
    def is_populated(self):
        """
            True if album populated
        """
        return True

#######################
# PROTECTED           #
#######################
    def _on_album_updated(self, scanner, album_id, added):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        if self._album.id == album_id and not added:
            self.destroy()

#######################
# PRIVATE             #
#######################
    def __set_play_all_image(self):
        """
            Set play all image based on current shuffle status
        """
        if App().settings.get_enum("shuffle") == Shuffle.NONE:
            self.__play_all_button.get_image().set_from_icon_name(
                "media-playlist-consecutive-symbolic",
                Gtk.IconSize.INVALID)
        else:
            self.__play_all_button.get_image().set_from_icon_name(
                "media-playlist-shuffle-symbolic",
                Gtk.IconSize.INVALID)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if self.__widget is None:
            return
        if surface is None:
            if self.__art_size == ArtSize.BIG:
                icon_size = Gtk.IconSize.DIALOG
            else:
                icon_size = Gtk.IconSize.DIALOG.DND
            self._artwork.set_from_icon_name("folder-music-symbolic",
                                             icon_size)
        else:
            self._artwork.set_from_surface(surface)
        self.show_all()
        self.emit("populated")

    def __on_artist_button_press(self, eventbox, event):
        """
            Go to artist page
            @param eventbox as Gtk.EventBox
            @param event as Gdk.EventButton
        """
        App().window.container.show_view([Type.ARTISTS],
                                         self._album.artist_ids)
        return True

    def __on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        self.__widget = None
