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

from gi.repository import Gtk, Gdk, GLib, Gio, GObject

from collections import OrderedDict

from lollypop.define import App, Type, Sizing, ViewType, MARGIN, MARGIN_SMALL
from lollypop.widgets_tracks import TracksWidget
from lollypop.widgets_row_playlist import PlaylistRow
from lollypop.objects import Track
from lollypop.utils import get_position_list


class PlaylistsWidget(Gtk.Grid):
    """
        Show playlist tracks/albums
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, playlist_ids, view_type):
        """
            Init playlist Widget
            @param playlist_ids as [int]
            @param view_type as ViewType
        """
        Gtk.Grid.__init__(self)
        self.set_row_spacing(5)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.__cancellable = Gio.Cancellable()
        self.__playlist_ids = playlist_ids
        self.__view_type = view_type
        self.__duration = 0
        self.__tracks = {}
        self.__row_tracks_left = []
        self.__row_tracks_right = []
        self.__width = None
        self.__orientation = None
        if view_type & ViewType.POPOVER:
            self.set_margin_start(MARGIN_SMALL)
        else:
            self.set_margin_start(MARGIN)
        self.set_margin_end(MARGIN)

        self.__grid = Gtk.Grid()
        self.__grid.set_vexpand(True)
        self.__grid.set_column_spacing(20)
        self.__grid.set_column_homogeneous(True)
        self.__grid.show()

        self.connect("size-allocate", self.__on_size_allocate)

        self.__tracks_widget_left = TracksWidget()
        self.__tracks_widget_left.set_vexpand("True")
        self.__tracks_widget_right = TracksWidget()
        self.__tracks_widget_right.set_vexpand("True")
        self.__tracks_widget_left.connect("activated",
                                          self.__on_activated)
        self.__tracks_widget_right.connect("activated",
                                           self.__on_activated)
        self.__tracks_widget_left.show()
        self.__tracks_widget_right.show()

        self.add(self.__grid)

    def set_filter_func(self, func):
        """
            Set filter function
        """
        self.__tracks_widget_left.set_filter_func(func)
        self.__tracks_widget_right.set_filter_func(func)

    def update_allocation(self):
        """
            Update widget allocation
        """
        self.__width = 0
        self.__on_size_allocate(self, self.get_allocation())

    def get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        ordinate = None
        for child in self.__tracks_widget_left.get_children() + \
                self.__tracks_widget_right.get_children():
            if child.track.id == App().player.current_track.id:
                ordinate = child.translate_coordinates(self.__grid, 0, 0)[1]
        return ordinate

    def populate(self, tracks):
        """
            Populate view with two columns
            @param tracks as [Track]
        """
        # We reset width here to allow size allocation code to run
        self.__width = None
        if self.__view_type & ViewType.TWO_COLUMNS:
            # We are looking for middle
            # Ponderate with this:
            # Tracks with cover == 2
            # Tracks without cover == 1
            prev_album_id = None
            heights = {}
            total = 0
            idx = 0
            for track in tracks:
                if track.album_id != prev_album_id:
                    heights[idx] = 2
                    total += 2
                else:
                    heights[idx] = 1
                    total += 1
                prev_album_id = track.album_id
                idx += 1
            half = int(total / 2 + 0.5)
            mid_tracks = 1
            count = 0
            for height in heights.values():
                count += height
                if count >= half:
                    break
                mid_tracks += 1
            tracks = get_position_list(tracks, 0)
            widgets = {self.__tracks_widget_left: tracks[:mid_tracks],
                       self.__tracks_widget_right: tracks[mid_tracks:]}
            self.__add_tracks(OrderedDict(widgets))
        else:
            tracks = get_position_list(tracks, 0)
            widgets = {self.__tracks_widget_left: tracks}
            self.__add_tracks(OrderedDict(widgets))
        if self.__view_type & ViewType.DND:
            self.connect("key-press-event", self.__on_key_press_event)

    def set_playing_indicator(self):
        """
            Set playing indicator
        """
        track_id = App().player.current_track.id
        self.__tracks_widget_left.update_playing(track_id)
        self.__tracks_widget_right.update_playing(track_id)

    def stop(self):
        """
            Stop loading
        """
        self.__cancellable.cancel()

    def append(self, track_id):
        """
            Add track to widget
            @param track_id as int
        """
        length = len(self.children)
        position = length + 1
        widgets = {self.__tracks_widget_right: [(Track(track_id), position)]}
        self.__add_tracks(OrderedDict(widgets))
        self.__make_homogeneous()

    def remove(self, track_id, position):
        """
            Remove track from widget
            @param track_id as int
            @param position as int
        """
        index = 0
        for row in self.children:
            if row.track.id == track_id and index == position:
                GLib.idle_add(row.destroy)
                self.__on_remove_track(row)
                break
            index += 1
        self.__make_homogeneous()

    @property
    def id(self):
        """
            Return playlist widget id
            @return int
        """
        return Type.PLAYLISTS

    @property
    def children(self):
        """
            Return all rows
            @return [Gtk.ListBoxRow]
        """
        rows = []
        for listbox in [self.__tracks_widget_left, self.__tracks_widget_right]:
            rows += listbox.get_children()
        return rows

    @property
    def duration(self):
        """
            Get duration
            @return int (seconds)
        """
        return self.__duration

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        return [self.__tracks_widget_left, self.__tracks_widget_right]

#######################
# PRIVATE             #
#######################
    def __make_homogeneous(self):
        """
            Move a track from right to left and vice versa
        """
        if len(self.__tracks_widget_right.get_children()) >\
                len(self.__tracks_widget_left.get_children()):
            child = self.__tracks_widget_right.get_children()[0]
            self.__tracks_widget_right.remove(child)
            self.__tracks_widget_left.add(child)
        elif len(self.__tracks_widget_left.get_children()) >\
                len(self.__tracks_widget_right.get_children()) + 1:
            child = self.__tracks_widget_left.get_children()[-1]
            self.__tracks_widget_left.remove(child)
            self.__tracks_widget_right.insert(child, 0)

    def __add_tracks(self, widgets, previous_tracks=[]):
        """
            Add tracks to list
            @param widgets as OrderedDict
            @internal previous_tracks
        """
        if self.__cancellable.is_cancelled():
            return

        # We are loading left then right then left then right then ...
        widget = next(iter(widgets))
        widgets.move_to_end(widget)
        tracks = widgets[widget]

        if not tracks:
            if not previous_tracks:
                # Link last left and first right
                left_children = self.__tracks_widget_left.get_children()
                right_children = self.__tracks_widget_right.get_children()
                if left_children and right_children:
                    last_left = left_children[-1]
                    first_right = right_children[0]
                    last_left.set_next_row(first_right)
                    first_right.set_previous_row(last_left)
                self.emit("populated")
            else:
                GLib.idle_add(self.__add_tracks, widgets, tracks)
            return
        (track, position) = tracks.pop(0)
        track.set_number(position + 1)
        self.__duration += track.duration
        row = PlaylistRow(track, self.__view_type)
        children = widget.get_children()
        previous_row = children[-1] if children else None
        row.set_previous_row(previous_row)
        if previous_row is not None:
            previous_row.set_next_row(row)
        if self.__view_type & ViewType.DND:
            row.connect("insert-track", self.__on_insert_track)
            row.connect("remove-track", self.__on_remove_track)
            row.connect("do-selection", self.__on_do_selection)
        row.show()
        widget.insert(row, position)
        GLib.idle_add(self.__add_tracks, widgets, tracks)

    def __on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__width == allocation.width:
            return
        self.__width = allocation.width
        redraw = False
        if allocation.width < Sizing.MONSTER or\
                not App().settings.get_value("split-view"):
            self.__grid.set_property("valign", Gtk.Align.START)
            orientation = Gtk.Orientation.VERTICAL
        else:
            self.__grid.set_property("valign", Gtk.Align.FILL)
            orientation = Gtk.Orientation.HORIZONTAL
        if orientation != self.__orientation:
            self.__orientation = orientation
            redraw = True
        self.__grid.set_orientation(orientation)
        if redraw:
            for child in self.__grid.get_children():
                self.__grid.remove(child)
            GLib.idle_add(self.__grid.add, self.__tracks_widget_left)
            GLib.idle_add(self.__grid.add, self.__tracks_widget_right)

    def __on_activated(self, widget, track):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track as Track
        """
        App().player.load(track)
        if not App().player.is_party:
            rows = self.__tracks_widget_left.get_children() +\
                   self.__tracks_widget_right.get_children()
            row_tracks = [row.track for row in rows]
            App().player.populate_playlist_by_tracks(row_tracks,
                                                     self.__playlist_ids,
                                                     track)

    def __on_insert_track(self, row, new_track_id, down):
        """
            Insert a new row at position
            @param row as PlaylistRow
            @param new_track_id as int
            @param down as bool
        """
        position = self.children.index(row)
        track = Track(new_track_id)
        new_row = PlaylistRow(track, self.__view_type)
        new_row.connect("insert-track", self.__on_insert_track)
        new_row.connect("remove-track", self.__on_remove_track)
        new_row.connect("do-selection", self.__on_do_selection)
        new_row.show()
        if down:
            position += 1
            new_row.set_previous_row(row)
            new_row.set_next_row(row.next_row)
            if row.next_row is not None:
                row.next_row.set_previous_row(new_row)
            row.set_next_row(new_row)
        else:
            new_row.set_previous_row(row.previous_row)
            new_row.set_next_row(row)
            if row.previous_row is not None:
                row.previous_row.set_next_row(new_row)
            row.set_previous_row(new_row)
        new_row.update_number(position + 1)
        left_count = len(self.__tracks_widget_left.get_children())
        if position < left_count:
            row.get_parent().insert(new_row, position)
        else:
            row.get_parent().insert(new_row, position - left_count)
        if self.__playlist_ids == App().player.playlist_ids:
            App().player.insert_track(track, position)
        if len(self.__playlist_ids) == 1 and self.__playlist_ids[0] >= 0:
            App().playlists.insert_track(self.__playlist_ids[0],
                                         track, position)
        self.__make_homogeneous()

    def __on_remove_track(self, row):
        """
            Remove row's track
            @param row as PlaylistRow
        """
        if self.__playlist_ids == App().player.playlist_ids:
            App().player.remove_track(row.track.id)
        if len(self.__playlist_ids) == 1 or self.__playlist_ids[0] > 0:
            App().playlists.remove_uri(self.__playlist_ids[0],
                                       row.track.uri)
        if row.previous_row is None:
            if row.next_row is not None:
                row.next_row.set_previous_row(None)
        elif row.next_row is None:
            if row.previous_row is not None:
                row.previous_row.set_next_row(None)
        else:
            row.next_row.set_previous_row(row.previous_row)
            row.previous_row.set_next_row(row.next_row)

    def __on_do_selection(self, row):
        """
            Select rows from start (or any selected row) to track
            @param row as Row
        """
        children = self.children
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

    def __on_key_press_event(self, widget, event):
        """
            Handle keyboard events (DEL, ...)
            @param widget as Gtk.Widget
            @param event as Gdk.EventKey
        """
        if event.keyval == Gdk.KEY_Delete:
            from lollypop.widgets_row_dnd import DNDRow
            for child in self.children:
                if child.get_state_flags() & Gtk.StateFlags.SELECTED:
                    DNDRow.destroy_track_row(child)
