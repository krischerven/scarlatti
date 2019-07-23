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

from gettext import gettext as _

from lollypop.widgets_album import AlbumWidget
from lollypop.helper_overlay_album import OverlayAlbumHelper
from lollypop.define import App, ArtSize, Shuffle, ViewType, ArtBehaviour
from lollypop.define import MARGIN_SMALL, Type
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
        self.__font_height = font_height
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        AlbumWidget.__init__(self, album, genre_ids, artist_ids)
        self.set_view_type(view_type)
        # No padding, we don't want user to activate widget while clicking
        # on toggle button
        self.get_style_context().add_class("no-padding")
        self.set_margin_start(MARGIN_SMALL)
        self.set_margin_end(MARGIN_SMALL)

    def populate(self):
        """
            Populate widget content
        """
        if self._artwork is None:
            OverlayAlbumHelper.__init__(self, self.__view_type)
            self._watch_loading = self._album.mtime <= 0
            grid = Gtk.Grid()
            grid.set_row_spacing(2)
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
            self._overlay = Gtk.Overlay.new()
            self._artwork = Gtk.Image.new()
            self._artwork.connect("realize", on_realize)
            self._overlay.add(self._artwork)
            toggle_button = Gtk.ToggleButton.new()
            toggle_button.set_image(self.__label)
            toggle_button.set_relief(Gtk.ReliefStyle.NONE)
            toggle_button.get_style_context().add_class("light-button")
            toggle_button.connect("toggled", self.__on_label_toggled)
            toggle_button.show()
            grid.add(self._overlay)
            grid.add(toggle_button)
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
        if self._artwork is not None:
            self._artwork.set_size_request(self.__art_size, self.__art_size)
            self._artwork.set_from_surface(None)

    def set_artwork(self):
        """
            Set artwork
        """
        if self._artwork is None:
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
        if self._artwork is not None:
            OverlayAlbumHelper.set_view_type(self, view_type)
        self.__view_type = view_type
        if self.__view_type & ViewType.SMALL:
            self.__art_size = ArtSize.MEDIUM
        elif self.__view_type & ViewType.MEDIUM:
            self.__art_size = ArtSize.BANNER
        else:
            self.__art_size = ArtSize.BIG
        self.set_size_request(self.__art_size,
                              self.__art_size + self.__font_height * 2)

    def show_overlay(self, show):
        """
            Set overlay
            @param show as bool
        """
        if self.is_set_overlay_valid(show):
            return
        OverlayAlbumHelper.show_overlay(self, show)
        if show:
            # Play all button
            self.__play_all_button = Gtk.Button.new()
            self.__play_all_button.set_property("has-tooltip", True)
            self.__play_all_button.set_tooltip_text(_("Play albums"))
            self.__play_all_button.connect("realize", on_realize)
            self.__play_all_button.connect("clicked",
                                           self.__on_play_all_clicked)
            self.__play_all_button.set_image(Gtk.Image())
            self.__play_all_button.get_image().set_pixel_size(self._pixel_size)
            self.__set_play_all_image()
            self.__play_all_button.show()
            self._small_grid.add(self.__play_all_button)
            self.__play_all_button.get_style_context().add_class(
               "overlay-button")
        else:
            self.__play_all_button.destroy()
            self.__play_all_button = None

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self._artwork is None:
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
        if self._artwork is None:
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

    def __on_play_all_clicked(self, button):
        """
            Play album with context
            @param button as Gtk.Button
        """
        from lollypop.view import View
        self._show_append(False)
        if App().player.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        view = self.get_ancestor(View)
        if view is not None:
            view.play_all_from(self)

    def __on_label_toggled(self, button):
        """
            Show tracks popover
            @param button as Gtk.ToggleButton
        """
        def on_closed(popover):
            button.set_active(False)

        if not button.get_active():
            return
        if App().window.is_adaptive:
            App().window.container.show_view([Type.ALBUM], self._album)
        else:
            from lollypop.pop_tracks import TracksPopover
            popover = TracksPopover(self._album)
            popover.set_relative_to(button)
            popover.set_position(Gtk.PositionType.BOTTOM)
            popover.connect("closed", on_closed)
            popover.popup()

    def __on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        self._artwork = None
