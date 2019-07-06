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

from gi.repository import GObject, Gtk, Pango, GLib

from lollypop.define import App, ArtSize, Type, ViewType, ArtBehaviour
from lollypop.widgets_row import Row
from lollypop.widgets_row_dnd import DNDRow


class PlaylistRow(Row, DNDRow):
    """
        A track row with album cover
    """
    __gsignals__ = {
        "insert-track": (
            GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "remove-track": (
            GObject.SignalFlags.RUN_FIRST, None, ()),
        "do-selection": (
            GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, track, view_type):
        """
            Init row widget
            @param track as Track
            @param view_type as ViewType
        """
        Row.__init__(self, track, track.album.artist_ids, view_type)
        if view_type & ViewType.DND:
            DNDRow.__init__(self)
        self._grid.insert_row(0)
        self._grid.insert_column(0)
        self._grid.insert_column(1)
        self._grid.attach(self._indicator, 1, 1, 1, 2)
        self.__artwork = Gtk.Image.new()
        App().art_helper.set_frame(self.__artwork,
                                   "small-cover-frame",
                                   ArtSize.MEDIUM,
                                   ArtSize.MEDIUM)
        self.__artwork.set_no_show_all(True)
        self.__artwork.set_margin_top(2)
        self.__artwork.set_margin_start(2)
        self.__artwork.set_margin_bottom(2)
        # We force width with a Box
        box = Gtk.Box()
        box.set_homogeneous(True)
        box.add(self.__artwork)
        box.set_property("width-request", ArtSize.MEDIUM + 2)
        self._grid.attach(box, 0, 0, 1, 2)
        self.show_all()
        self.__header = Gtk.Grid()
        self.__header.set_column_spacing(5)
        if self._track.album.artist_ids[0] != Type.COMPILATIONS:
            self.__album_artist_label = Gtk.Label.new()
            self.__album_artist_label.set_markup(
                "<b>" +
                GLib.markup_escape_text(
                    ", ".join(self._track.album.artists)) +
                "</b>")
            self.__album_artist_label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__album_artist_label.get_style_context().add_class(
                "dim-label")
            self.__header.add(self.__album_artist_label)
        self.__album_label = Gtk.Label.new(self._track.album.name)
        self.__album_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__album_label.get_style_context().add_class("dim-label")
        self.__album_label.set_hexpand(True)
        self.__album_label.set_property("halign", Gtk.Align.END)
        self.__header.add(self.__album_label)
        if self._artists_label is not None:
            self._grid.attach(self.__header, 1, 0, 5, 1)
        else:
            self._grid.attach(self.__header, 1, 0, 4, 1)
        self.set_indicator()

    def set_previous_row(self, row):
        """
            Set previous row
            @param row as Row
        """
        if self._view_type & ViewType.DND:
            Row.set_previous_row(self, row)
        self.update_artwork_state()

    def update_artwork_state(self):
        """
            Update artwork state based on previous
        """
        if self.previous_row is None or\
                self.previous_row.track.album.id != self.track.album.id:
            self.show_artwork()
        else:
            self.hide_artwork()

    def show_artwork(self):
        """
            Show row artwork
        """
        if not self.__artwork.get_visible():
            self.__artwork.set_tooltip_text(self._track.album.name)
            App().art_helper.set_album_artwork(
                                           self.track.album,
                                           ArtSize.MEDIUM,
                                           ArtSize.MEDIUM,
                                           self.__artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE |
                                           ArtBehaviour.CROP_SQUARE,
                                           self.__on_album_artwork)

    def hide_artwork(self):
        """
            Hide row artwork
        """
        self.__artwork.set_tooltip_text("")
        self.__artwork.clear()
        self.__artwork.hide()
        self.__header.hide()

    @property
    def filter(self):
        """
            @return str
        """
        return " ".join(self._track.album.artists +
                        self._track.artists +
                        [self._track.name] +
                        [self._track.album.name])

#######################
# PROTECTED           #
#######################
    def _get_menu(self):
        """
            Return TrackMenu
        """
        from lollypop.menu_objects import TrackMenu
        return TrackMenu(self._track, True)

    def _on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        Row._on_destroy(self, widget)
        if self._view_type & ViewType.DND:
            DNDRow._on_destroy(self, widget)
        self.__artwork = None

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
            self.__artwork.set_from_icon_name("folder-music-symbolic",
                                              Gtk.IconSize.BUTTON)
        else:
            self.__artwork.set_from_surface(surface)
        self.__artwork.show()
        self.show_all()
