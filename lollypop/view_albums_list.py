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

from lollypop.utils import popup_widget
from lollypop.view_lazyloading import LazyLoadingView
from lollypop.define import App, ViewType, MARGIN
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.widgets_row_album import AlbumRow
from lollypop.helper_gestures import GesturesHelper


class AlbumsListView(LazyLoadingView, ViewController, GesturesHelper):
    """
        View showing albums
    """

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init widget
            @param genre_ids as int
            @param artist_ids as int
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self.__width = 0
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self.__reveals = []
        # Calculate default album height based on current pango context
        # We may need to listen to screen changes
        self.__height = AlbumRow.get_best_height(self)
        self._box = Gtk.ListBox()
        self._box.set_margin_bottom(MARGIN)
        self._box.set_margin_end(MARGIN)
        self._box.get_style_context().add_class("trackswidget")
        self._box.set_vexpand(True)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.show()
        GesturesHelper.__init__(self, self._box)
        if view_type & ViewType.DND:
            from lollypop.helper_dnd import DNDHelper
            self.__dnd_helper = DNDHelper(self._box, view_type)
            self.__dnd_helper.connect("dnd-insert", self.__on_dnd_insert)
        self.add_widget(self._box)

    def add_reveal_albums(self, albums):
        """
            Add albums to reveal list
            @param albums as [Album]
        """
        self.__reveals += list(albums)

    def insert_album(self, album, index):
        """
            Insert album at index
            @param album as Album
            @param index as int
        """
        children = self.children
        if children and\
                index < len(children) + 1 and\
                children[index].album.id == album.id:
            children[index].tracks_view.append_rows(album.tracks)
        else:
            row = AlbumRow(album, self.__height, self._view_type)
            row.populate()
            self.insert_row(row, index)

    def insert_row(self, row, index):
        """
            Insert row at index
            @param row as AlbumRow
            @param index as int
        """
        row.connect("activated", self.__on_row_activated)
        row.show()
        self._box.insert(row, index)

    def populate(self, albums):
        """
            Populate widget with album rows
            @param albums as [Album]
        """
        for child in self._box.get_children():
            GLib.idle_add(child.destroy)
        LazyLoadingView.populate(self, albums)

    def jump_to_current(self):
        """
            Scroll to album
        """
        y = self.__get_current_ordinate()
        if y is not None:
            self._scrolled.get_vadjustment().set_value(y)

    def clear(self, clear_albums=False):
        """
            Clear the view
        """
        for child in self._box.get_children():
            GLib.idle_add(child.destroy)
        if clear_albums:
            App().player.clear_albums()

    def set_width(self, width):
        """
            Set list width
            @param width as int
        """
        self.set_property("halign", Gtk.Align.CENTER)
        self.__width = width

    def do_get_preferred_width(self):
        if self.__width == 0:
            return LazyLoadingView.do_get_preferred_width(self)
        else:
            return (self.__width, self.__width)

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"genre_ids": self.__genre_ids,
                "artist_ids": self.__artist_ids,
                "view_type": self.view_type}

    @property
    def dnd_helper(self):
        """
            Get Drag & Drop helper
            @return DNDHelper
        """
        return self.__dnd_helper

    @property
    def box(self):
        """
            Get album list box
            @return Gtk.ListBox
        """
        return self._box

    @property
    def children(self):
        """
            Get view children
            @return [AlbumRow]
        """
        return self._box.get_children()

#######################
# PROTECTED           #
#######################
    def _get_child(self, album):
        """
            Get an album view widget
            @param album as Album
            @return AlbumRow
        """
        if self.destroyed:
            return None
        row = AlbumRow(album, self.__height, self._view_type)
        row.connect("activated", self.__on_row_activated)
        row.show()
        self._box.add(row)
        return row

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self._box.get_children():
            child.set_playing_indicator()

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self._box.get_children():
            if child.album.id == album_id:
                child.set_artwork()

    def _on_duration_changed(self, player, track_id):
        """
            Update track duration
            @param player as Player
            @param track_id as int
        """
        for child in self.children:
            child.tracks_view.update_duration(track_id)

    def _on_primary_long_press_gesture(self, x, y):
        """
            Show row menu
            @param x as int
            @param y as int
        """
        self.__popup_menu(x, y)

    def _on_primary_press_gesture(self, x, y, event):
        """
            Activate current row
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        row = self._box.get_row_at_y(y)
        if row is None:
            return
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        row.reveal()

    def _on_secondary_press_gesture(self, x, y, event):
        """
            Show row menu
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        self._on_primary_long_press_gesture(x, y)

    def _on_populated(self, widget):
        """
            Add another album/disc
            @param widget as AlbumWidget/TracksView
        """
        if widget.album in self.__reveals:
            widget.reveal()
            self.__reveals.remove(widget.album)
        else:
            LazyLoadingView._on_populated(self, widget)

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, x, y):
        """
            Popup menu for album
            @param x as int
            @param y as int
        """
        def on_hidden(popover, hide, row):
            row.unset_state_flags(Gtk.StateFlags.CHECKED)

        row = self._box.get_row_at_y(y)
        if row is None:
            return
        from lollypop.menu_objects import AlbumMenu
        from lollypop.widgets_menu import MenuBuilder
        menu = AlbumMenu(row.album, ViewType.ALBUM,
                         App().window.is_adaptive)
        menu_widget = MenuBuilder(menu)
        menu_widget.show()
        popover = popup_widget(menu_widget, self._box, x, y)
        if popover is not None:
            popover.connect("hidden", on_hidden, row)
        row.set_state_flags(Gtk.StateFlags.CHECKED, True)

    def __reveal_row(self, row):
        """
            Reveal row if style always present
        """
        style_context = row.get_style_context()
        if style_context.has_class("drag-down"):
            row.reveal(True)

    def __get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        y = None
        for child in self._box.get_children():
            if child.album.id == App().player.current_track.album.id:
                child.reveal(True)
                y = child.translate_coordinates(self._box, 0, 0)[1]
        return y

    def __on_dnd_insert(self, dnd_helper, row, index):
        """
            Insert row at index
            @param dnd_helper as DNDHelper
            @param row as AlbumRow
            @param index as int
        """
        self.insert_row(row, index)

    def __on_row_activated(self, row, track):
        """
            Start playback
            @param row as AlbumRow
            @param track_id as int
        """
        # In party mode, just play track_id and continue party mode
        if App().player.is_party or self._view_type & ViewType.PLAYBACK:
            App().player.load(track)
        elif self._view_type & ViewType.PLAYLISTS:
            albums = []
            for album_row in self.children:
                albums.append(album_row.album)
            App().player.play_track_for_albums(track, albums)
        else:
            App().player.remove_album_by_id(track.album.id)
            App().player.add_album(track.album)
            App().player.load(track)
