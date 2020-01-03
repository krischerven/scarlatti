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

from gi.repository import Gtk, GLib, GObject

from lollypop.define import App, ViewType, MARGIN, ScanUpdate
from lollypop.view_tracks_album import AlbumTracksView
from lollypop.widgets_banner_album import AlbumBannerWidget
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.view_lazyloading import LazyLoadingView
from lollypop.helper_filtering import FilteringHelper
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.logger import Logger
from lollypop.objects_album import Album


class AlbumView(FilteringHelper, LazyLoadingView,
                ViewController, SignalsHelper):
    """
        Show artist albums and tracks
    """

    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    @signals_map
    def __init__(self, album, view_type):
        """
            Init ArtistView
            @param album as Album
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        FilteringHelper.__init__(self)
        self.__album = album
        self.__others_boxes = []
        self.__grid = Gtk.Grid()
        self.__grid.show()
        self.__grid.set_row_spacing(10)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__banner = AlbumBannerWidget(self.__album, self._view_type)
        self.add_widget(self.__grid, self.__banner)
        return [
            (App().scanner, "scan-finished", "_on_scan_finished"),
            (App().scanner, "album-updated", "_on_album_updated")
        ]

    def populate(self):
        """
            Populate the view with album
        """
        self.__tracks_view = AlbumTracksView(self.__album, ViewType.ALBUM)
        self.__tracks_view.show()
        self.__tracks_view.connect("populated", self.__on_tracks_populated)
        self.__tracks_view.set_margin_start(MARGIN)
        self.__tracks_view.set_margin_end(MARGIN)
        self.__tracks_view.populate()
        self.__grid.add(self.__tracks_view)

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
                    if hasattr(child, "data"):
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
            Get default args for __class__
            @return {}
        """
        return {"album": self.__album, "view_type": self.view_type}

    @property
    def filtered(self):
        """
            Get filtered children
            @return [Gtk.Widget]
        """
        filtered = self.__tracks_view.children
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
        return self.__tracks_view

    @property
    def is_populated(self):
        """
            True if populated
            @return bool
        """
        return True

#######################
# PROTECTED           #
#######################
    def _on_scan_finished(self, scanner, modifications):
        """
            Reload album if needed
            @param scanner as CollectionScanner
            @param modifications as bool
        """
        if not self.get_sensitive():
            App().window.container.reload_view()

    def _on_album_updated(self, scanner, album_id, scan_update):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param scan_update as ScanUpdate
        """
        if album_id != self.__album.id:
            return
        if scan_update == ScanUpdate.REMOVED:
            App().window.container.go_back()
        elif scan_update == ScanUpdate.MODIFIED:
            self.set_sensitive(False)
            self.__album = Album(self.__album.id)

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        self.__tracks_view.set_playing_indicator()

    def _on_duration_changed(self, player, track_id):
        """
            Update track duration
            @param player as Player
            @param track_id as int
        """
        self.__tracks_view.update_duration(track_id)

#######################
# PRIVATE             #
#######################
    def __on_tracks_populated(self, view):
        """
            Populate remaining discs
            @param view as TracksView
        """
        if self.__tracks_view.is_populated:
            self.emit("populated")
            self.__banner.show()
            if self._view_type & ViewType.OVERLAY:
                from lollypop.view_albums_line import AlbumsArtistLineView
                for artist_id in self.__album.artist_ids:
                    others_box = AlbumsArtistLineView(self.__album, artist_id,
                                                      ViewType.SMALL |
                                                      ViewType.ALBUM |
                                                      ViewType.SCROLLED)
                    others_box.set_margin_start(MARGIN)
                    others_box.set_margin_end(MARGIN)
                    others_box.populate()
                    self.__grid.add(others_box)
                    self.__others_boxes.append(others_box)
        else:
            self.__tracks_view.populate()
