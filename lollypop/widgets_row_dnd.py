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

from gi.repository import Gtk, Gdk, GLib

from lollypop.define import App, ArtSize
from lollypop.logger import Logger


class DNDRow:
    """
        Allow Drag & drop on a Row
    """
    __autoscroll_timeout_id = None

    def destroy_track_row(r):
        """
            Properly destroy a Row
            @param r as Row
        """
        r.emit("remove-track")
        r.destroy()
        if r.previous_row is not None:
            r.previous_row.set_next_row(r.next_row)
            r.previous_row.update_number(
                r.previous_row.track.number)
        else:
            r.update_number(r.track.number - 1)
        if r.next_row is not None:
            r.next_row.set_previous_row(r.previous_row)

    def __init__(self):
        """
            Init drag & drop
        """
        self.__drag_data_delete_id = None
        self.__timeout_id = None
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [],
                             Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()
        self.connect("drag-begin", self.__on_drag_begin)
        self.connect("drag-data-get", self.__on_drag_data_get)
        self.connect("drag-data-received", self.__on_drag_data_received)
        self.connect("drag-leave", self.__on_drag_leave)
        self.connect("drag-motion", self.__on_drag_motion)

    def update_number(self, position):
        """
            Update row number
            @param position as int
        """
        if App().settings.get_value("show-tag-tracknumber"):
            return
        self._track.set_number(position)
        self.update_number_label()
        if self.next_row is not None:
            self.next_row.update_number(position + 1)

#######################
# PROTECTED           #
#######################
    def _on_destroy(self, widget):
        """
            Update label
            @param widget as Gtk.Widget
        """
        if self.next_row is not None:
            position = self._track.number
            self.next_row.update_number(position)

#######################
# PRIVATE             #
#######################
    def __auto_scroll(self, up):
        """
            Auto scroll up/down
            @param up as bool
        """
        adj = self.get_ancestor(Gtk.ScrolledWindow).get_vadjustment()
        value = adj.get_value()
        if up:
            adj_value = value - ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() == 0:
                DNDRow.__autoscroll_timeout_id = None
                return False
        else:
            adj_value = value + ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() < adj_value:
                DNDRow.__autoscroll_timeout_id = None
                return False
        return True

    def __on_drag_begin(self, row, context):
        """
            @param row as RowDND
            @param context as Gdk.DragContext
        """
        row.set_state_flags(Gtk.StateFlags.SELECTED, True)
        if self.__drag_data_delete_id is None:
            self.__drag_data_delete_id = self.connect(
                                                  "drag-data-delete",
                                                  self.__on_drag_data_delete)

    def __on_drag_data_delete(self, row, context):
        """
            Destroy row and update neighbours
            @param row as RowDND
            @param context as Gdk.DragContext
        """
        if row.get_parent() != self.get_parent():
            return
        if hasattr(row, "_track"):
            # Delete all selected rows
            r = row.previous_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    DNDRow.destroy_track_row(r)
                r = r.previous_row
            r = row.next_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    DNDRow.destroy_track_row(r)
                r = r.next_row
            DNDRow.destroy_track_row(row)
        elif hasattr(row, "_album"):
            self.emit("remove-album")
            row.destroy()

    def __on_drag_data_get(self, row, context, data, info, time):
        """
            Get DND data for current row
            @param row as RowDND
            @param context as Gdk.DragContext
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
        """
        import json
        wstr = str(row)
        if hasattr(self, "_track"):
            track_ids = []
            # Delete all selected rows
            r = row.previous_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    track_ids.append(r.track.id)
                r = r.previous_row
            track_ids.append(self.track.id)
            r = row.next_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    track_ids.append(r.track.id)
                r = r.next_row
            info = {"data": (wstr, track_ids)}
        elif hasattr(self, "_album"):
            album_ids = {}
            # Delete all selected rows
            r = row.previous_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    album_ids[r.album.id] = r.album.track_ids
                r = r.previous_row
            album_ids[row.album.id] = row.album.track_ids
            r = row.next_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    album_ids[r.album.id] = r.album.track_ids
                r = r.next_row
            info = {"data": (wstr, album_ids)}
        text = json.dumps(info)
        data.set_text(text, len(text))

    def __on_drag_data_received(self, row, context, x, y, data, info, time):
        """
            Move track
            @param row as RowDND
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param data as Gtk.SelectionData
            @param info as int
            @param time as int
            @param timeout as bool
        """
        def on_drag_data_received(row, context, x, y, data, info, time):
            height = self.get_allocated_height()
            if y > height / 2:
                down = True
            else:
                down = False
            try:
                import json
                info = json.loads(data.get_text())
                (wstr, ids) = info["data"]
                if str(row) == wstr:
                    self.disconnect(self.__drag_data_delete_id)
                    self.__drag_data_delete_id = None
                    return
                if wstr.find("AlbumRow") == -1:
                    for track_id in ids:
                        self.emit("insert-track", track_id, down)
                else:
                    for key in ids.keys():
                        self.emit("insert-album", int(key), ids[key], down)
            except Exception as e:
                Logger.error("DNDRow::on_drag_data_received(): %s", e)
        # We want delete before insert
        GLib.idle_add(on_drag_data_received, row, context,
                      x, y, data, info, time)

    def __on_drag_motion(self, row, context, x, y, time):
        """
            Add style
            @param row as RowDND
            @param context as Gdk.DragContext
            @param x as int
            @param y as int
            @param time as int
        """
        row_height = row.get_allocated_height()
        if y < row_height / 2:
            row.get_style_context().add_class("drag-up")
            row.get_style_context().remove_class("drag-downg")
        elif y > row_height / 2:
            row.get_style_context().add_class("drag-down")
            row.get_style_context().remove_class("drag-up")
        scrolled = row.get_ancestor(Gtk.ScrolledWindow)
        (row_x, row_y) = row.translate_coordinates(scrolled, 0, 0)
        auto_scroll = False
        up = row_y + y <= ArtSize.MEDIUM
        if up:
            auto_scroll = True
        elif row_y + y >= scrolled.get_allocated_height() - ArtSize.MEDIUM:
            auto_scroll = True
        if DNDRow.__autoscroll_timeout_id is None and auto_scroll:
            DNDRow.__autoscroll_timeout_id = GLib.timeout_add(
                                                            100,
                                                            self.__auto_scroll,
                                                            up)
        elif DNDRow.__autoscroll_timeout_id is not None and not auto_scroll:
            GLib.source_remove(DNDRow.__autoscroll_timeout_id)
            DNDRow.__autoscroll_timeout_id = None

    def __on_drag_leave(self, row, context, time):
        """
            @param row as RowDND
            @param context as Gdk.DragContext
            @param time as int
        """
        row.get_style_context().remove_class("drag-up")
        row.get_style_context().remove_class("drag-down")
