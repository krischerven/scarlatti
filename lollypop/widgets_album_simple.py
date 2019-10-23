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

from lollypop.define import App, ArtSize, ViewType, ArtBehaviour
from lollypop.define import MARGIN_SMALL
from lollypop.utils import on_query_tooltip, set_cursor_type, emit_signal


class AlbumSimpleWidget(Gtk.FlowBoxChild):
    """
        Album widget showing cover, artist and title
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
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
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.__album = album
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self.__artwork = None
        self.__font_height = font_height
        self.set_view_type(view_type)
        self.set_property("halign", Gtk.Align.START)
        self.set_property("valign", Gtk.Align.START)

    def populate(self):
        """
            Populate widget content
        """
        if self.__artwork is None:
            grid = Gtk.Grid()
            grid.set_row_spacing(MARGIN_SMALL)
            grid.set_orientation(Gtk.Orientation.VERTICAL)
            self.__label = Gtk.Label.new()
            self.__label.set_justify(Gtk.Justification.CENTER)
            self.__label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__label.set_property("halign", Gtk.Align.CENTER)
            self.__label.set_property("has-tooltip", True)
            self.__label.connect("query-tooltip", on_query_tooltip)
            style_context = self.__label.get_style_context()
            if self.__view_type & ViewType.SMALL:
                style_context.add_class("text-small")
            else:
                style_context.add_class("padding")
            album_name = GLib.markup_escape_text(self.__album.name)
            if self.__view_type & ViewType.ALBUM:
                self.__label.set_markup(album_name)
            else:
                artist_name = GLib.markup_escape_text(", ".join(
                                                      self.__album.artists))
                self.__label.set_markup(
                    "<b>%s</b>\n<span alpha='50000'>%s</span>" % (album_name,
                                                                  artist_name))
            self.__artwork = Gtk.Image.new()
            self.__artwork.connect("realize", set_cursor_type)
            grid.add(self.__artwork)
            grid.add(self.__label)
            self.set_artwork()
            self.set_selection()
            self.connect("destroy", self.__on_destroy)
            self.add(grid)
        else:
            self.set_artwork()

    def disable_artwork(self):
        """
            Disable widget artwork
        """
        if self.__artwork is not None:
            self.__artwork.set_size_request(self.__art_size, self.__art_size)
            self.__artwork.set_from_surface(None)

    def set_artwork(self):
        """
            Set artwork
        """
        if self.__artwork is None:
            return
        if self.__art_size < ArtSize.BIG:
            frame = "small-cover-frame"
        else:
            frame = "cover-frame"
        App().art_helper.set_frame(self.__artwork,
                                   frame,
                                   self.__art_size,
                                   self.__art_size)
        App().art_helper.set_album_artwork(self.__album,
                                           self.__art_size,
                                           self.__art_size,
                                           self.__artwork.get_scale_factor(),
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
        elif self.__view_type & ViewType.ADAPTIVE:
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
        if self.__artwork is None:
            return (0, 0)
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        if self.__artwork is None:
            return
        selected = self.__album.id == App().player.current_track.album.id
        if selected:
            self.__artwork.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self.__artwork.set_state_flags(Gtk.StateFlags.NORMAL, True)

    @property
    def data(self):
        """
            @return Album
        """
        return self.__album

    @property
    def name(self):
        """
            Get name
            @return str
        """
        return "%s %s" % (self.__album.name, self.__album.artists)

    @property
    def artwork(self):
        """
            Get album artwork
            @return Gtk.Image
        """
        return self.__artwork

    @property
    def is_populated(self):
        """
            True if album populated
        """
        return True

#######################
# PRIVATE             #
#######################
    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if self.__artwork is None:
            return
        if surface is None:
            if self.__art_size == ArtSize.BIG:
                icon_size = Gtk.IconSize.DIALOG
            else:
                icon_size = Gtk.IconSize.DIALOG.DND
            self.__artwork.set_from_icon_name("folder-music-symbolic",
                                              icon_size)
        else:
            self.__artwork.set_from_surface(surface)
        self.show_all()
        emit_signal(self, "populated")

    def __on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        self.__artwork = None
