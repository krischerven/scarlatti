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

from gi.repository import Gtk, GLib

from lollypop.define import App, ViewType, MARGIN
from lollypop.view_tracks import TracksView
from lollypop.widgets_banner_album import AlbumBannerWidget
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.view import LazyLoadingView
from lollypop.helper_filtering import FilteringHelper
from lollypop.logger import Logger


class AlbumView(LazyLoadingView, TracksView, ViewController, FilteringHelper):
    """
        Show artist albums and tracks
    """

    def __init__(self, album, view_type):
        """
            Init ArtistView
            @param album as Album
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type)
        TracksView.__init__(self, App().window, None)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        FilteringHelper.__init__(self)
        self._album = album
        self.__others_boxes = []
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
        """
        TracksView.populate(self)
        self.__grid.add(self._responsive_widget)
        self.__banner = AlbumBannerWidget(self._album,
                                          self._view_type | ViewType.ALBUM)
        self._overlay = Gtk.Overlay.new()
        if self._view_type & ViewType.SCROLLED:
            self._overlay.add(self._scrolled)
            self._viewport.add(self.__grid)
        else:
            self._overlay.add(self.__grid)
        self._overlay.show()
        self.__banner.show()
        self._overlay.add_overlay(self.__banner)
        self.add(self._overlay)
        self._responsive_widget.show()

    def activate_child(self):
        """
            Activated typeahead row
        """
        try:
            if App().player.is_party:
                App().lookup_action("party").change_state(
                    GLib.Variant("b", False))
            for child in self.filtered:
                style_context = child.get_style_context()
                if style_context.has_class("typeahead"):
                    if hasattr(child, "album"):
                        child.activate()
                    else:
                        track = child.track
                        App().player.add_album(track.album)
                        App().player.load(track.album.get_track(track.id))
        except Exception as e:
            Logger.error("AlbumView::activate_child: %s" % e)

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        view_type = self._view_type & ~self.view_sizing_mask
        return ({"album": self._album,
                 "view_type": view_type},
                self._sidebar_id,
                position)

    @property
    def filtered(self):
        """
            Get filtered children
            @return [Gtk.Widget]
        """
        filtered = self.children
        for box in self.__others_boxes:
            for child in box.children:
                filtered.append(child)
        return filtered

    @property
    def scroll_shift(self):
        """
            Add scroll shift on y axes
            @return int
        """
        return self.__banner.height

    @property
    def scroll_relative_to(self):
        """
            Relative to scrolled widget
            @return Gtk.Widget
        """
        return self._responsive_widget

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
            self.__banner.collapse(False)
        else:
            self.__banner.collapse(True)

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        self.set_playing_indicator()

    def _on_duration_changed(self, player, track_id):
        """
            Update track duration
            @param player as Player
            @param track_id as int
        """
        self.update_duration(track_id)

    def _on_album_updated(self, scanner, album_id, added):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        # Check we are not destroyed
        if album_id == self._album.id and not added:
            App().window.go_back()
            return

    def _on_map(self, widget):
        """
            Set initial state and connect signals
            @param widget as Gtk.Widget
        """
        LazyLoadingView._on_map(self, widget)
        self._responsive_widget.set_margin_top(
            self.__banner.height)
        if self._view_type & ViewType.SCROLLED:
            self._scrolled.get_vscrollbar().set_margin_top(
                    self.__banner.height)

    def _on_tracks_populated(self, disc_number):
        """
            Emit populated signal
            @param disc_number as int
        """
        if TracksView.get_populated(self):
            from lollypop.view_albums_box import OthersAlbumsBoxView
            for artist_id in self._album.artist_ids:
                others_box = OthersAlbumsBoxView(self._album, artist_id,
                                                 ViewType.SMALL |
                                                 ViewType.ALBUM)
                others_box.populate()
                self.__grid.add(others_box)
                self.__others_boxes.append(others_box)
        else:
            TracksView.populate(self)

    def _on_adaptive_changed(self, window, status):
        """
            Update banner style
            @param window as Window
            @param status as bool
        """
        LazyLoadingView._on_adaptive_changed(self, window, status)
        self.__banner.set_view_type(self._view_type)
        self._responsive_widget.set_margin_top(self.__banner.height)
        if self._view_type & ViewType.SCROLLED:
            self._scrolled.get_vscrollbar().set_margin_top(
                    self.__banner.height)
