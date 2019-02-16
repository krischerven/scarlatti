# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gettext import gettext as _

from lollypop.define import App, ViewType, Type, MARGIN
from lollypop.objects import Album
from lollypop.utils import remove_static_genres
from lollypop.view_tracks import TracksView
from lollypop.widgets_album_banner import AlbumBannerWidget
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.view import LazyLoadingView


class AlbumView(LazyLoadingView, TracksView, ViewController):
    """
        Show artist albums and tracks
    """

    def __init__(self, album, artist_ids, genre_ids):
        """
            Init ArtistView
            @param album as Album
            @param artist_ids as [int]
            @param genre_ids as [int]
        """
        view_type = ViewType.TWO_COLUMNS | ViewType.MULTIPLE
        LazyLoadingView.__init__(self, view_type)
        TracksView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self._album = album
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self.__genre_ids = remove_static_genres(genre_ids)
        self.__grid = Gtk.Grid()
        self.__grid.set_property("vexpand", True)
        self.__grid.set_row_spacing(10)
        self.__grid.set_margin_start(MARGIN)
        self.__grid.set_margin_end(MARGIN)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.show()

    def populate(self):
        """
            Populate the view with album
            @param albums as [Album]
        """
        TracksView.populate(self)
        self.__grid.add(self._responsive_widget)
        self._viewport.add(self.__grid)
        self._overlay = Gtk.Overlay.new()
        self._overlay.add(self._scrolled)
        self._overlay.show()
        self.__banner = AlbumBannerWidget(self._album)
        self.__banner.show()
        self._overlay.add_overlay(self.__banner)
        self.add(self._overlay)
        self._responsive_widget.show()

#######################
# PROTECTED           #
#######################
    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        LazyLoadingView._on_value_changed(self, adj)
        if adj.get_value() == adj.get_lower():
            self.__banner.set_height(self.__banner.default_height)
        else:
            self.__banner.set_height(self.__banner.default_height / 3)

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        self.set_playing_indicator()

    def _on_map(self, widget):
        """
            Connect signals and set active ids
            @param widget as Gtk.Widget
        """
        self._responsive_widget.set_margin_top(
            self.__banner.default_height + 15)
        App().window.emit("show-can-go-back", True)
        App().window.emit("can-go-back-changed", True)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", self.__genre_ids))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", self.__artist_ids))

    def _on_tracks_populated(self, disc_number):
        """
            Emit populated signal
            @param disc_number as int
        """
        if TracksView.get_populated(self):
            from lollypop.view_albums_box import AlbumsBoxView
            for artist_id in self.__artist_ids:
                if artist_id == Type.COMPILATIONS:
                    album_ids = App().albums.get_compilation_ids(
                        self.__genre_ids)
                else:
                    album_ids = App().albums.get_ids(
                        [artist_id], [])
                if self._album.id in album_ids:
                    album_ids.remove(self._album.id)
                if not album_ids:
                    continue
                artist = App().artists.get_name(artist_id)
                label = Gtk.Label.new()
                label.set_markup(
                                 '''<span size="large" alpha="40000"
                                     weight="bold">%s %s</span>''' %
                                 (_("Others albums from"), artist))
                label.set_property("halign", Gtk.Align.START)
                label.show()
                self.__grid.add(label)
                others_box = AlbumsBoxView([],
                                           [artist_id],
                                           ViewType.SMALL)
                others_box.show()
                self.__grid.add(others_box)
                others_box.populate([Album(id) for id in album_ids])
        else:
            TracksView.populate(self)

#######################
# PRIVATE             #
#######################
