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

from gi.repository import Gdk, Gtk, GLib

from lollypop.objects_album import Album


class DNDHelper:
    """
        Helper for DND of AlbumsListView
    """

    def __init__(self, listbox, view_type):
        """
            Init helper
            @param listbox as Gtk.ListBox
            @params view_type as ViewType
        """
        self.__listbox = listbox
        self.__view_type = view_type
        self.__drag_begin_row = None
        listbox.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                                Gdk.DragAction.MOVE)
        listbox.drag_source_add_text_targets()
        listbox.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                              [], Gdk.DragAction.MOVE)
        listbox.drag_dest_add_text_targets()
        listbox.connect("drag-begin", self.__on_drag_begin)
        listbox.connect("drag-leave", self.__on_drag_leave)
        listbox.connect("drag-motion", self.__on_drag_motion)
        listbox.connect("drag-data-get", self.__on_drag_data_get)
        listbox.connect("drag-data-received", self.__on_drag_data_received)

#######################
# PROTECTED           #
#######################
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

    def update_album_rows(self):
        """
            Merge album rows and update track position
        """
        def merge_if_possible(row1, row2, children):
            if row1 is None or row2 is None:
                return
            if row1.album.id == row2.album.id:
                row1.album.append_tracks(row2.album.tracks)
                row1.append_rows(row2.album.tracks)
                if row2 in children:
                    children.remove(row2)
                row2.destroy()

        children = self.__listbox.get_children()
        while children:
            row = children.pop(0)
            index = row.get_index()
            next = self.__listbox.get_row_at_index(index + 1)
            merge_if_possible(row, next, children)
        position = 1
        for row in self.__listbox.get_children():
            position = row.update_track_position(position)

    def __insert_album_row_at_album_row(self, src_row, dst_row, direction):
        """
            Insert src album row at dst album row
            @param src_row as AlbumRow
            @param dst_row as AlbumRow
            @param direction as Gtk.DirectionType
        """
        src_index = src_row.get_index()
        if src_index != -1:
            self.__listbox.remove(src_row)
        dst_index = dst_row.get_index()
        if direction == Gtk.DirectionType.DOWN:
            self.__listbox.insert(src_row, dst_index)
        else:
            self.__listbox.insert(src_row, dst_index)
        # After all current events are finished
        GLib.idle_add(self.update_album_rows, priority=GLib.PRIORITY_LOW)

    def __insert_track_row_at_album_row(self, src_row, dst_row, direction):
        """
            Insert src track row at dst album row
            @param src_row as TrackRow
            @param dst_row as AlbumRow
            @param direction as Gtk.DirectionType
        """
        from lollypop.widgets_row_album import AlbumRow
        height = AlbumRow.get_best_height(src_row)
        new_album = Album(src_row.track.album.id)
        new_album.set_tracks([src_row.track])
        new_album_row = AlbumRow(new_album, height, self.__view_type,
                                 True, None, 0)
        new_album_row.show()
        new_album_row.populate()
        self.__insert_album_row_at_album_row(new_album_row,
                                             dst_row, direction)
        # If last track row, delete album row
        album_row = src_row.get_ancestor(AlbumRow)
        if len(album_row.children) == 1:
            album_row.destroy()
        else:
            src_row.track.album.remove_track(src_row.track)
            src_row.destroy()

    def __insert_album_row_at_track_row(self, src_row, dst_album_row,
                                        dst_row, direction):
        """
            Insert album track row at dst track row
            @param src_row as TrackRow
            @param dst_album_row as AlbumRow
            @param dst_row as TrackRow
            @param direction as Gtk.DirectionType
        """
        from lollypop.widgets_row_album import AlbumRow
        height = AlbumRow.get_best_height(src_row)
        # First split dst album
        index = dst_album_row.children.index(dst_row)
        if direction == Gtk.DirectionType.DOWN:
            index += 1
        rows = dst_album_row.children[:index]
        split_album = Album(dst_album_row.album.id)
        split_album.set_tracks([row.track for row in rows])
        split_album_row = AlbumRow(split_album, height, self.__view_type,
                                   True, None, 0)
        split_album_row.show()
        split_album_row.populate()
        for row in rows:
            dst_album_row.album.remove_track(row.track)
            row.destroy()
        self.__insert_album_row_at_album_row(src_row, dst_album_row,
                                             Gtk.DirectionType.DOWN)
        self.__insert_album_row_at_album_row(split_album_row, src_row,
                                             Gtk.DirectionType.DOWN)

    def __insert_track_row_at_track_row(self, src_row, dst_album_row,
                                        dst_row, direction):
        """
            Insert src track row at dst track row
            @param src_row as TrackRow
            @param dst_album_row as AlbumRow
            @param dst_row as TrackRow
            @param direction as Gtk.DirectionType
        """
        from lollypop.widgets_row_album import AlbumRow
        height = AlbumRow.get_best_height(src_row)
        # First split dst album
        index = dst_album_row.children.index(dst_row)
        if direction == Gtk.DirectionType.DOWN:
            index += 1
        rows = dst_album_row.children[:index]
        split_album = Album(dst_album_row.album.id)
        split_album.set_tracks([row.track for row in rows])
        split_album_row = AlbumRow(split_album, height, self.__view_type,
                                   True, None, 0)
        split_album_row.show()
        split_album_row.populate()
        for row in rows:
            dst_album_row.album.remove_track(row.track)
            row.destroy()
        # Create new album
        new_album = Album(src_row.track.album.id)
        new_album.set_tracks([src_row.track])
        new_album_row = AlbumRow(new_album, height, self.__view_type,
                                 True, None, 0)
        new_album_row.show()
        new_album_row.populate()
        self.__insert_album_row_at_album_row(new_album_row, dst_album_row,
                                             Gtk.DirectionType.DOWN)
        self.__insert_album_row_at_album_row(split_album_row, new_album_row,
                                             Gtk.DirectionType.DOWN)

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

    def __on_drag_begin(self, listbox, context):
        """
            @param listbox as Gtk.ListBox
            @param context as Gdk.DragContext
        """
        self.__drag_begin_row = None
        for row in self.__listbox.get_children():
            if row.revealed:
                for subrow in row.children:
                    if subrow.get_state_flags() & Gtk.StateFlags.PRELIGHT:
                        self.__drag_begin_row = subrow
                        break
            if self.__drag_begin_row:
                break
            if row.get_state_flags() & Gtk.StateFlags.PRELIGHT:
                self.__drag_begin_row = row
                break

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
        row = listbox.get_row_at_y(y)
        if row is None:
            return
        row_height = row.get_allocated_height()
        (row_x, row_y) = row.translate_coordinates(listbox, 0, 0)
        if y < row_y + 20:
            row.get_style_context().add_class("drag-up")
        elif y > row_y + row_height - 20:
            row.get_style_context().add_class("drag-down")
        if row.revealed:
            for subrow in row.children:
                (subrow_x, subrow_y) = subrow.translate_coordinates(listbox,
                                                                    0, 0)
                subrow_height = subrow.get_allocated_height()
                if y > subrow_y and y < subrow_y + subrow_height / 2:
                    subrow.get_style_context().add_class("drag-up")
                elif y > subrow_y + subrow_height / 2 and\
                        y < subrow_y + subrow_height:
                    subrow.get_style_context().add_class("drag-down")

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
        from lollypop.widgets_row_track import TrackRow
        album_row = listbox.get_row_at_y(y)
        # Search for any track row at y
        if album_row is not None:
            track_listbox = album_row.boxes[0]
            (tx, ty) = track_listbox.translate_coordinates(listbox, 0, 0)
            track_row = track_listbox.get_row_at_y(y - ty)
            if track_row is not None:
                row = track_row
            else:
                row = album_row
        if row is None or self.__drag_begin_row is None:
            return
        row_height = row.get_allocated_height()
        (row_x, row_y) = row.translate_coordinates(listbox, 0, 0)
        if y < row_y + row_height / 2:
            direction = Gtk.DirectionType.UP
        elif y > row_y - row_height / 2:
            direction = Gtk.DirectionType.DOWN
        if isinstance(row, TrackRow):
            if isinstance(self.__drag_begin_row, TrackRow):
                self.__insert_track_row_at_track_row(
                    self.__drag_begin_row, album_row, row, direction)
            else:
                self.__insert_album_row_at_track_row(
                    self.__drag_begin_row, album_row, row, direction)
        elif isinstance(self.__drag_begin_row, TrackRow):
            self.__insert_track_row_at_album_row(
                self.__drag_begin_row, row, direction)
        else:
            self.__insert_album_row_at_album_row(
                self.__drag_begin_row, row, direction)
        self.__unmark_all_rows()
