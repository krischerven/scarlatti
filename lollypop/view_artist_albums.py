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

from lollypop.view import LazyLoadingView
from lollypop.define import ViewType
from lollypop.widgets_album_detailed import AlbumDetailedWidget
from lollypop.controller_view import ViewController, ViewControllerType


class ArtistAlbumsView(LazyLoadingView, ViewController):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_ids, genre_ids, view_type):
        """
            Init ArtistAlbumsView
            @param artist_ids as [int]
            @param genre_ids as [int]
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type | ViewType.FILTERED)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self._artist_ids = artist_ids
        self._genre_ids = genre_ids
        self._album_box = Gtk.Grid()
        self._album_box.set_row_spacing(50)
        self._album_box.set_orientation(Gtk.Orientation.VERTICAL)
        self._album_box.set_property("valign", Gtk.Align.START)
        self._album_box.show()
        self._viewport.add(self._album_box)
        self._overlay = Gtk.Overlay.new()
        self._overlay.add(self._scrolled)
        self._overlay.show()
        self.add(self._overlay)

    def populate(self, albums):
        """
            Populate the view
            @param albums as [Album]
        """
        self.__add_albums(albums)

    def stop(self):
        """
            Stop current loading widget
        """
        LazyLoadingView.stop(self)
        for child in self.children:
            child.stop()

    @property
    def children(self):
        """
            Get children
            @return AlbumDetailedwidget
        """
        children = []
        for child in self._album_box.get_children():
            if isinstance(child, AlbumDetailedWidget):
                children.append(child)
        return children

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self.children:
            child.set_selection()
            child.set_playing_indicator()

    def _on_duration_changed(self, player, track_id):
        """
            Update track duration
            @param player as Player
            @param track_id as int
        """
        for child in self.children:
            child.update_duration(track_id)

    def _on_search_changed(self, entry):
        """
            Update filter
            @param entry as Gtk.Entry
        """
        self._filter = entry.get_text()
        for child in self.children:
            for box in child.boxes:
                box.invalidate_filter()

    def _on_populated(self, widget, idle_id):
        """
            Add another album/disc
            @param widget as AlbumWidget/TracksView
            @param idle_id as int
        """
        LazyLoadingView._on_populated(self, widget, idle_id)
        if widget.is_populated:
            widget.set_filter_func(self._filter_func)
            widget.set_opacity(1)

#######################
# PRIVATE             #
#######################
    def __add_albums(self, albums):
        """
            Pop an album and add it to the view,
            repeat operation until album list is empty
            @param albums as [Album]
        """
        if self._lazy_queue is None:
            return
        if albums:
            album = albums.pop(0)
            widget = AlbumDetailedWidget(album,
                                         self._genre_ids,
                                         self._artist_ids,
                                         self._view_type)
            widget.set_opacity(0)
            widget.show()
            self._lazy_queue.append(widget)
            self._album_box.add(widget)
            GLib.idle_add(self.__add_albums, albums)
        else:
            self.lazy_loading()
