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

from gi.repository import Gtk, GLib, GObject, Gdk

from gettext import gettext as _

from lollypop.utils import get_icon_name, do_shift_selection
from lollypop.view import LazyLoadingView
from lollypop.helper_size_allocation import SizeAllocationHelper
from lollypop.objects_album import Album
from lollypop.define import App, ViewType, MARGIN, Type, Sizing
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.widgets_row_album import AlbumRow
from lollypop.helper_gestures import GesturesHelper


class AlbumsListView(LazyLoadingView, ViewController, SizeAllocationHelper,
                     GesturesHelper):
    """
        View showing albums
    """

    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "remove-from-playlist": (GObject.SignalFlags.RUN_FIRST, None,
                                 (GObject.TYPE_PYOBJECT,))
    }

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init widget
            @param genre_ids as int
            @param artist_ids as int
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        self._albums = []
        self.__position = 0
        self.__track_position_id = None
        if genre_ids and genre_ids[0] < 0:
            if genre_ids[0] == Type.WEB and\
                    GLib.find_program_in_path("youtube-dl") is None:
                self._empty_message = _("Missing youtube-dl command")
            self._empty_icon_name = get_icon_name(genre_ids[0])
        self.__autoscroll_timeout_id = None
        self.__reveals = []
        self.__prev_animated_rows = []
        # Calculate default album height based on current pango context
        # We may need to listen to screen changes
        self.__height = AlbumRow.get_best_height(self)
        self._box = Gtk.ListBox()
        if view_type & ViewType.PLAYLISTS:
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

        if view_type & ViewType.PLAYLISTS:
            SizeAllocationHelper.__init__(self)
        if view_type & ViewType.SCROLLED:
            self._scrolled.set_property("expand", True)
            self.add(self._scrolled)
        else:
            self.add(self._box)

    def set_reveal(self, albums):
        """
            Set albums to reveal on populate
            @param albums as [Album]
        """
        self.__reveals = albums

    def set_margin_top(self, margin):
        """
            Set margin on box
            @param margin as int
        """
        self._box.set_margin_top(margin + MARGIN)

    def insert_album(self, album, reveal, position, cover_uri=None):
        """
            Add an album
            @param album as Album
            @param reveal as bool
            @param position as int
            @param cover_uri as str
        """
        row = None
        if row is None:
            row = self.__row_for_album(album, reveal, cover_uri)
            row.populate()
            row.show()
            self._box.insert(row, position)
        else:
            row.append_rows(album.tracks)
        if self._view_type & ViewType.SCROLLED:
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)
        elif self._box not in self.get_children():
            self.add(self._box)

    def populate(self, albums):
        """
            Populate widget with album rows
            @param albums as [Album]
        """
        if albums:
            self._lazy_queue = []
            for child in self._box.get_children():
                GLib.idle_add(child.destroy)
            self.__add_albums(list(albums))
            self._albums = albums
        else:
            LazyLoadingView.populate(self)

    def jump_to_current(self, scrolled=None):
        """
            Scroll to album
            @param scrolled as Gtk.Scrolled/None
        """
        if scrolled is None:
            scrolled = self._scrolled
        y = self.__get_current_ordinate()
        if y is not None:
            scrolled.get_vadjustment().set_value(y)

    def clear(self, clear_albums=False):
        """
            Clear the view
        """
        for child in self._box.get_children():
            GLib.idle_add(child.destroy)
        if clear_albums:
            App().player.clear_albums()

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
        return ({"genre_ids": self.__genre_ids,
                 "artist_ids": self.__artist_ids,
                 "view_type": view_type},
                self._sidebar_id, position)

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
    def _handle_size_allocate(self, allocation):
        """
            Change view width
            @param allocation as Gtk.Allocation
        """
        if SizeAllocationHelper._handle_size_allocate(self, allocation):
            if allocation.width < Sizing.BIG:
                margin = MARGIN
            else:
                margin = allocation.width / 4
            self._box.set_margin_start(margin)
            self._box.set_margin_end(margin)

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
            child.update_duration(track_id)

    def _on_album_updated(self, scanner, album_id, added):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        if self._view_type & (ViewType.SEARCH | ViewType.DND):
            return
        if added:
            album_ids = App().window.container.get_view_album_ids(
                                            self.__genre_ids,
                                            self.__artist_ids)
            if album_id not in album_ids:
                return
            index = album_ids.index(album_id)
            self.insert_album(Album(album_id), False, index)
        else:
            for child in self._box.get_children():
                if child.album.id == album_id:
                    child.destroy()

    def _on_primary_long_press_gesture(self, x, y):
        """
            Show row menu
            @param x as int
            @param y as int
        """
        self.__popup_menu(self, x, y)

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
        if event.state & Gdk.ModifierType.CONTROL_MASK and\
                self._view_type & ViewType.POPOVER:
            self._box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        elif event.state & Gdk.ModifierType.SHIFT_MASK and\
                self._view_type & ViewType.POPOVER:
            self._box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
            do_shift_selection(self._box, row)
        else:
            self._box.set_selection_mode(Gtk.SelectionMode.NONE)
            if self._view_type & ViewType.PLAYLISTS and row.album.tracks:
                track = row.album.tracks[0]
                albums = []
                for child in self._box.get_children():
                    albums.append(child.album)
                App().player.play_track_for_albums(track, albums)
            else:
                row.reveal()

    def _on_secondary_press_gesture(self, x, y, event):
        """
            Show row menu
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        self._on_primary_long_press_gesture(x, y)

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, widget, xcoordinate=None, ycoordinate=None):
        """
            Popup menu for album
            @param eventbox as Gtk.EventBox
            @param xcoordinate as int (or None)
            @param ycoordinate as int (or None)
        """
        def on_closed(widget):
            self.get_style_context().remove_class("track-menu-selected")

        from lollypop.menu_objects import AlbumMenu
        menu = AlbumMenu(self._album, ViewType.ALBUM)
        popover = Gtk.Popover.new_from_model(widget, menu)
        popover.connect("closed", on_closed)
        self.get_style_context().add_class("track-menu-selected")
        if xcoordinate is not None and ycoordinate is not None:
            rect = Gdk.Rectangle()
            rect.x = xcoordinate
            rect.y = ycoordinate
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
        popover.popup()

    def __reveal_row(self, row):
        """
            Reveal row if style always present
        """
        style_context = row.get_style_context()
        if style_context.has_class("drag-down"):
            row.reveal(True)

    def __add_albums(self, albums):
        """
            Add items to the view
            @param albums ids as [Album]
        """
        if self._lazy_queue is None or self.destroyed:
            return
        if albums:
            album = albums.pop(0)
            row = self.__row_for_album(album, album in self.__reveals)
            row.show()
            self._box.add(row)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_albums, albums)
        else:
            # If only one album, we want to reveal it
            # Stop lazy loading and populate
            children = self._box.get_children()
            if len(children) == 1:
                self.stop()
                children[0].populate()
                children[0].reveal(True)
            else:
                self.lazy_loading()
            if self._view_type & ViewType.SCROLLED:
                if self._viewport.get_child() is None:
                    self._viewport.add(self._box)
            elif self._box not in self.get_children():
                self.add(self._box)

    def __row_for_album(self, album, reveal=False, cover_uri=None):
        """
            Get a row for track id
            @param album as Album
            @param reveal as bool
            @param cover_uri as str
        """
        row = AlbumRow(album, self.__height, self._view_type,
                       reveal, cover_uri, self.__position)
        # For Playlists, we want track position not track number
        if self._view_type & ViewType.PLAYLISTS:
            self.__position += len(album.tracks)
        else:
            self.__position = 0
        row.connect("remove-from-playlist", self.__on_remove_from_playlist)
        return row

    def __get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        y = None
        for child in self._box.get_children():
            if child.album == App().player.current_track.album:
                child.populate()
                child.reveal(True)
                y = child.translate_coordinates(self._box, 0, 0)[1]
        return y

    def __on_remove_from_playlist(self, row, object):
        """
            Pass signal to parent
        """
        self.emit("remove-from-playlist", object)
