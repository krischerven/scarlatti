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

from gi.repository import Gdk, Gtk, GLib, GObject

from lollypop.objects_album import Album
from lollypop.widgets_row_album import AlbumRow
from lollypop.widgets_row_track import TrackRow


class DNDHelper(GObject.Object):
    """
        Helper for DND of AlbumsListView
    """

    __gsignals__ = {
        "dnd-finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, listbox, view_type):
        """
            Init helper
            @param listbox as Gtk.ListBox
            @params view_type as ViewType
        """
        GObject.Object.__init__(self)
        self.__listbox = listbox
        self.__view_type = view_type
        self.__drag_begin_rows = []
        listbox.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                                Gdk.DragAction.MOVE)
        listbox.drag_source_add_text_targets()
        listbox.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                              [], Gdk.DragAction.MOVE)
        listbox.drag_dest_add_text_targets()
        self.__gesture = Gtk.GestureDrag.new(listbox)
        self.__gesture.connect("drag-begin", self.__on_drag_begin)
        listbox.connect("drag-leave", self.__on_drag_leave)
        listbox.connect("drag-motion", self.__on_drag_motion)
        listbox.connect("drag-data-get", self.__on_drag_data_get)
        listbox.connect("drag-data-received", self.__on_drag_data_received)

#######################
# PRIVATE             #
#######################
    def __get_album_row_for_track(self, track_row):
        """
            Get album row for track row
            @param track_row as TrackRow
            @return AlbumRow
        """
        for row in self.__listbox.get_children():
            if track_row in row.children:
                return row
        return None

    def __update_album_rows(self):
        """
            Merge album rows and update track position
        """
        def merge_if_possible(row1, row2):
            if row1 is None or row2 is None:
                return False
            if row1.album.id == row2.album.id:
                row1.album.append_tracks(row2.album.tracks)
                row1.append_rows(row2.album.tracks)
                return True
            return False

        children = self.__listbox.get_children()
        while children:
            row = children[0]
            index = row.get_index()
            next = self.__listbox.get_row_at_index(index + 1)
            if merge_if_possible(row, next):
                children.remove(next)
                next.destroy()
            else:
                children.pop(0)
                row.show()
        GLib.idle_add(self.emit, "dnd-finished", priority=GLib.PRIORITY_LOW)

    def __do_drag_and_drop(self, src_rows, dest_row, direction):
        """
            Drag source rows at destination row with direction
            @param src_rows as [Row]
            @param dest_row as Row
            @param direction as Gtk.DirectionType
        """
        # Build new rows
        new_rows = self.__get_rows_from_rows(
            src_rows, AlbumRow.get_best_height(dest_row))
        # Insert new rows
        if isinstance(dest_row, TrackRow):
            album_row = dest_row.get_ancestor(AlbumRow)
            if album_row is None:
                return
            split_album_row = self.__split_album_row(album_row,
                                                     dest_row,
                                                     direction)
            index = album_row.get_index()
            if split_album_row is not None:
                self.__listbox.insert(split_album_row, index)
            index += 1
            for row in new_rows:
                self.__listbox.insert(row, index)
                index += 1
        else:
            index = dest_row.get_index()
            if direction == Gtk.DirectionType.DOWN:
                index += 1
            for row in new_rows:
                self.__listbox.insert(row, index)
                index += 1
        self.__destroy_rows(src_rows)
        GLib.idle_add(self.__update_album_rows, priority=GLib.PRIORITY_LOW)

    def __split_album_row(self, album_row, track_row, direction):
        """
            Split album row at track row with direction
            @param album_row as AlbumRow
            @param track_row as TrackRow
            @param direction as Gtk.DirectionType
            @return AlbumRow
        """
        height = AlbumRow.get_best_height(album_row)
        # First split dst album
        children = album_row.children
        index = children.index(track_row)
        if direction == Gtk.DirectionType.DOWN:
            index += 1
        if index + 1 > len(children):
            return None
        rows = album_row.children[:index]
        split_album = Album(album_row.album.id)
        split_album.set_tracks([row.track for row in rows])
        split_album_row = AlbumRow(split_album, height, self.__view_type,
                                   True)
        for row in rows:
            empty = album_row.album.remove_track(row.track)
            if empty:
                album_row.destroy()
            row.destroy()
        return split_album_row

    def __get_rows_from_rows(self, rows, height):
        """
            Build news rows from rows
            @return [TrackRow/AlbumRow]
            @param height as int
        """
        new_rows = []
        for row in rows:
            if isinstance(row, TrackRow):
                # Merge with previous
                if new_rows and new_rows[-1].album.id == row.track.album.id:
                    new_rows[-1].append_row(row.track)
                # Create a new album
                else:
                    new_album = Album(row.track.album.id)
                    new_album.set_tracks([row.track])
                    new_album_row = AlbumRow(new_album, height,
                                             self.__view_type, True)
                    new_rows.append(new_album_row)
            else:
                # Merge with previous
                if new_rows and new_rows[-1].album.id == row.album.id:
                    new_rows[-1].append_rows(row.album.tracks)
                # Create a new album
                else:
                    new_album = Album(row.album.id)
                    new_album.set_tracks(row.album.tracks)
                    new_album_row = AlbumRow(new_album, height,
                                             self.__view_type, False)
                    new_rows.append(new_album_row)
        return new_rows

    def __destroy_rows(self, rows):
        """
            Destroy rows and parent if needed
            @param rows as [Row]
        """
        for row in rows:
            if isinstance(row, TrackRow):
                album_row = row.get_ancestor(AlbumRow)
                if album_row is not None:
                    empty = album_row.album.remove_track(row.track)
                    if empty:
                        album_row.destroy()
                    row.destroy()
            else:
                row.destroy()

    def __unmark_all_rows(self):
        """
            Undrag all rows
        """
        for row in self.__listbox.get_children():
            context = row.get_style_context()
            context.remove_class("drag-up")
            context.remove_class("drag-down")
            if row.revealed:
                for subrow in row.children:
                    context = subrow.get_style_context()
                    context.remove_class("drag-up")
                    context.remove_class("drag-down")

    def __get_row_at_y(self, y):
        """
            Get row at position
            @param y as int
            @return (Gtk.ListBox, Row)
        """
        row = self.__listbox.get_row_at_y(y)
        if row.revealed:
            (listbox, subrow) = self.__get_subrow_at_y(row, y)
            if subrow is not None:
                return (listbox, subrow)
        return (self.__listbox, row)

    def __get_subrow_at_y(self, album_row, y):
        """
            Get subrow as position
            @param album_row as AlbumRow
            @param y as int
            @return (Gtk.ListBox, Row)
        """
        if album_row is not None:
            listbox = album_row.listbox
            (tx, ty) = listbox.translate_coordinates(self.__listbox, 0, 0)
            track_row = listbox.get_row_at_y(y - ty)
            if track_row is not None:
                return (listbox, track_row)
        return (None, None)

    def __on_drag_begin(self, gesture, x, y):
        """
            @param gesture as Gtk.GestureDrag
            @param x as int
            @param y as int
        """
        self.__drag_begin_rows = []
        (listbox, row) = self.__get_row_at_y(y)
        if row is not None:
            self.__drag_begin_rows += [row]
        for row in listbox.get_selected_rows():
            if row not in self.__drag_begin_rows:
                self.__drag_begin_rows.append(row)

    def __on_drag_leave(self, listbox, context, time):
        """
            @param listbox as Gtk.ListBox
            @param context as Gdk.DragContext
            @param time as int
        """
        self.__unmark_all_rows()

    def __on_drag_motion(self, listbox, context, x, y, time):
        """
            Add style
            @param listbox as Gtk.ListBox
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param time as int
        """
        self.__unmark_all_rows()
        (ignore, row) = self.__get_row_at_y(y)
        if row is None:
            return
        row_height = row.get_allocated_height()
        (row_x, row_y) = row.translate_coordinates(listbox, 0, 0)
        if y < row_y + 20:
            row.get_style_context().add_class("drag-up")
        elif y > row_y + row_height - 20:
            row.get_style_context().add_class("drag-down")

    def __on_drag_data_get(self, listbox, context, data, info, time):
        """
            Unused
        """
        data.set_text(" ", len(" "))

    def __on_drag_data_received(self, listbox, context, x, y,
                                data, info, time):
        """
            @param listbox as Gtk.ListBox
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
            @param timeout as bool
        """
        if not self.__drag_begin_rows:
            return
        (_listbox, row) = self.__get_row_at_y(y)
        if row is not None:
            row_height = row.get_allocated_height()
            (row_x, row_y) = row.translate_coordinates(listbox, 0, 0)
            if y < row_y + row_height / 2:
                direction = Gtk.DirectionType.UP
            elif y > row_y - row_height / 2:
                direction = Gtk.DirectionType.DOWN
            self.__do_drag_and_drop(self.__drag_begin_rows,
                                    row, direction)
        self.__unmark_all_rows()
