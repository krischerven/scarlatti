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

from gettext import gettext as _

from lollypop.utils import get_icon_name
from lollypop.view import LazyLoadingView
from lollypop.helper_size_allocation import SizeAllocationHelper
from lollypop.objects import Album, Track
from lollypop.define import ArtSize, App, ViewType, MARGIN, Type
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.widgets_row_album import AlbumRow


class AlbumsListView(LazyLoadingView, ViewController, SizeAllocationHelper):
    """
        View showing albums
    """

    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init widget
            @param genre_ids as int
            @param artist_ids as int
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type | ViewType.FILTERED)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
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
        self._box.set_margin_end(MARGIN)
        self._box.get_style_context().add_class("trackswidget")
        self._box.set_vexpand(True)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.set_activate_on_single_click(True)
        self._box.show()
        if view_type & ViewType.PLAYLISTS:
            SizeAllocationHelper.__init__(self)
        self._scrolled.set_property("expand", True)
        self.add(self._scrolled)

    def set_reveal(self, albums):
        """
            Set albums to reveal on populate
            @param albums as [Album]
        """
        self.__reveals = albums

    def insert_album(self, album, reveal, position, cover_uri=None):
        """
            Add an album
            @param album as Album
            @param reveal as bool
            @param position as int
            @param cover_uri as str
        """
        row = self.__row_for_album(album, reveal, cover_uri)
        children = self._box.get_children()
        if children:
            previous_row = children[position]
            row.set_previous_row(previous_row)
            previous_row.set_next_row(row)
        row.populate()
        row.show()
        self._box.insert(row, position)
        if self._viewport.get_child() is None:
            self._viewport.add(self._box)

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
        else:
            LazyLoadingView.populate(self)

    def rows_animation(self, x, y):
        """
            Show animation to help user dnd
            @param x as int
            @param y as int
        """
        # FIXME autoscroll continue after drop
        self.clear_animation()
        for row in self._box.get_children():
            coordinates = row.translate_coordinates(self, 0, 0)
            if coordinates is None:
                continue
            (row_x, row_y) = coordinates
            row_width = row.get_allocated_width()
            row_height = row.get_allocated_height()
            if x < row_x or\
                    x > row_x + row_width or\
                    y < row_y or\
                    y > row_y + row_height:
                continue
            if y <= row_y + ArtSize.MEDIUM / 2:
                self.__prev_animated_rows.append(row)
                row.get_style_context().add_class("drag-up")
                break
            elif y >= row_y + row_height - ArtSize.MEDIUM / 2:
                self.__prev_animated_rows.append(row)
                row.get_style_context().add_class("drag-down")
                GLib.timeout_add(1000, self.__reveal_row, row)
                break
            else:
                subrow = row.rows_animation(x, y, self)
                if subrow is not None:
                    self.__prev_animated_rows.append(subrow)

    def clear_animation(self):
        """
            Clear any animation
        """
        for row in self.__prev_animated_rows:
            ctx = row.get_style_context()
            ctx.remove_class("drag-up")
            ctx.remove_class("drag-down")

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
            if App().window.is_adaptive:
                margin = 0
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

    def _on_map(self, widget):
        """
            Connect signals and set active ids
            @param widget as Gtk.Widget
        """
        LazyLoadingView._on_map(self, widget)
        if not self.__genre_ids and not self.__artist_ids:
            return
        if self.__genre_ids:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__genre_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", self.__artist_ids))
        else:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__artist_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", []))
        App().settings.set_value("state-three-ids",
                                 GLib.Variant("ai", []))

#######################
# PRIVATE             #
#######################
    def __reveal_row(self, row):
        """
            Reveal row if style always present
        """
        style_context = row.get_style_context()
        if style_context.has_class("drag-down"):
            row.reveal(True)

    def __add_albums(self, albums, previous_row=None):
        """
            Add items to the view
            @param albums ids as [Album]
            @param previous_row as AlbumRow
        """
        if self._lazy_queue is None or self._viewport is None:
            return
        if albums:
            album = albums.pop(0)
            row = self.__row_for_album(album, album in self.__reveals)
            row.set_previous_row(previous_row)
            if previous_row is not None:
                previous_row.set_next_row(row)
            row.show()
            self._box.add(row)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_albums, albums, row)
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
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)

    def __row_for_album(self, album, reveal=False, cover_uri=None):
        """
            Get a row for track id
            @param album as Album
            @param reveal as bool
            @param cover_uri as str
        """
        row = AlbumRow(album, self.__height, self._view_type,
                       reveal, cover_uri, self, self.__position)
        self.__position += len(album.tracks)
        row.connect("insert-track", self.__on_insert_track)
        row.connect("insert-album", self.__on_insert_album)
        row.connect("insert-album-after", self.__on_insert_album_after)
        row.connect("remove-album", self.__on_remove_album)
        row.connect("do-selection", self.__on_do_selection)
        row.connect("track-activated", self.__on_track_activated)
        return row

    def __auto_scroll(self, up):
        """
            Auto scroll up/down
            @param up as bool
        """
        adj = self._scrolled.get_vadjustment()
        value = adj.get_value()
        if up:
            adj_value = value - ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() == 0:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().add_class("drag-up")
        else:
            adj_value = value + ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() < adj_value:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().add_class("drag-down")
                self.get_style_context().remove_class("drag-up")
        return True

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

    def __update_albums_positions(self):
        """
            Update track position for all albums
        """
        self.__track_position_id = None
        position = 1
        for child in self._box.get_children():
            position = child.update_tracks_position(position)

    def __on_track_activated(self, row, track):
        """
            Play playlist and track
            @param row as AlbumRow
            @param track as Track
        """
        albums = []
        for child in self._box.get_children():
            albums.append(child.album)
        App().player.play_albums(albums, track)

    def __on_insert_track(self, row, new_track_id, down):
        """
            Insert a new row at position
            @param row as PlaylistRow
            @param new_track_id as int
            @param down as bool
        """
        new_track = Track(new_track_id)
        children = self._box.get_children()
        position = children.index(row)
        lenght = len(children)
        if down:
            position += 1
        # Append track to current/next album
        if position < lenght and\
                children[position].album.id == new_track.album.id:
            new_track.set_album(children[position].album)
            children[position].prepend_rows([new_track])
            children[position].album.insert_track(new_track, 0)
        # Append track to previous/current album
        elif position - 1 < lenght and\
                children[position - 1].album.id == new_track.album.id:
            new_track.set_album(children[position - 1].album)
            children[position - 1].append_rows([new_track])
            children[position - 1].album.insert_track(new_track)
        # Add a new album
        else:
            album = Album(new_track.album.id)
            album.set_tracks([new_track])
            new_row = self.__row_for_album(
                                          album,
                                          self._view_type & ViewType.PLAYLISTS)
            new_row.populate()
            new_row.show()
            self._box.insert(new_row, position)
            App().player.add_album(album, position)
            if row.previous_row is not None and\
                    row.previous_row.album.id ==\
                    App().player.current_track.album.id:
                App().player.set_next()
                App().player.set_prev()
        if self.__track_position_id is not None:
            GLib.source_remove(self.__track_position_id)
        self.__track_position_id = GLib.idle_add(
            self.__update_albums_positions)

    def __on_insert_album(self, row, new_album_id, track_ids, down):
        """
            Insert a new row at position
            @param row as AlbumRow
            @param new_track_id as int
            @param track_ids as [int]
            @param down as bool
        """
        position = self._box.get_children().index(row)
        if down:
            position += 1
        album = Album(new_album_id)
        album.set_tracks([Track(track_id) for track_id in track_ids])
        new_row = self.__row_for_album(album,
                                       self._view_type & ViewType.PLAYLISTS)
        new_row.populate()
        new_row.show()
        self._box.insert(new_row, position)
        App().player.add_album(album, position)
        if self.__track_position_id is not None:
            GLib.source_remove(self.__track_position_id)
        self.__track_position_id = GLib.idle_add(
            self.__update_albums_positions)

    def __on_insert_album_after(self, view, after_album, album):
        """
            Insert album after after_album
            @param view as TracksView
            @param after_album as Album
            @param album as Album
        """
        position = 0
        children = self._box.get_children()
        # If after_album is undefined, prepend)
        if after_album.id is not None:
            for row in children:
                if row.album == after_album:
                    break
                position += 1
        new_row = self.__row_for_album(album,
                                       self._view_type & ViewType.PLAYLISTS)
        new_row.populate()
        new_row.set_previous_row(children[position])
        new_row.set_next_row(children[position].next_row)
        children[position].set_next_row(new_row)
        if new_row.next_row is not None:
            new_row.next_row.set_previous_row(new_row)
        new_row.show()
        self._box.insert(new_row, position + 1)
        App().player.add_album(album, position + 1)
        if self.__track_position_id is not None:
            GLib.source_remove(self.__track_position_id)
        self.__track_position_id = GLib.idle_add(
            self.__update_albums_positions)

    def __on_remove_album(self, row):
        """
            Remove album from player
            @param row as AlbumRow
        """
        if self._view_type & ViewType.POPOVER:
            App().player.remove_album(row.album)

    def __on_do_selection(self, row):
        """
            Select rows from start (or any selected row) to track
            @param row as AlbumRow
        """
        children = self._box.get_children()
        selected = None
        end = children.index(row) + 1
        for child in children:
            if child == row:
                break
            if child.get_state_flags() & Gtk.StateFlags.SELECTED:
                selected = child
        if selected is None:
            start = 0
        else:
            start = children.index(selected)
        for child in children[start:end]:
            child.set_state_flags(Gtk.StateFlags.SELECTED, True)
        for child in children[end:]:
            child.set_state_flags(Gtk.StateFlags.NORMAL, True)
