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

from gi.repository import GLib, Gtk, Gdk, Gio, GObject, Pango

from gettext import gettext as _
from collections import OrderedDict

from lollypop.define import Sizing
from lollypop.widgets_tracks import TracksWidget
from lollypop.widgets_row_track import TrackRow
from lollypop.objects import Album, Track
from lollypop.logger import Logger
from lollypop.utils import get_position_list, on_realize
from lollypop.define import App, Type, ViewType


class TracksView:
    """
        Responsive view showing discs on one or two rows
        Need to be inherited by an Album widget (AlbumListView, AlbumWidget)
    """
    __gsignals__ = {
        "album-added": (GObject.SignalFlags.RUN_FIRST, None,
                        (int, GObject.TYPE_PYOBJECT)),
        "album-moved": (GObject.SignalFlags.RUN_FIRST, None,
                        (int, GObject.TYPE_PYOBJECT)),
        "track-append": (GObject.SignalFlags.RUN_FIRST, None,
                         (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "track-removed": (GObject.SignalFlags.RUN_FIRST, None,
                          (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "insert-album-after": (GObject.SignalFlags.RUN_FIRST, None,
                               (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))
    }

    def __init__(self, view_type):
        """
            Init widget
            @param view_type as ViewType
        """
        if App().settings.get_value("force-single-column"):
            view_type &= ~ViewType.TWO_COLUMNS
        self._view_type = view_type
        self._width = None
        self.__discs = []
        self._responsive_widget = None
        self._orientation = None
        self.__populated = False
        self.__allocation_timeout_id = None
        self.__cancellable = Gio.Cancellable()

    def set_playing_indicator(self):
        """
            Set playing indicator
        """
        try:
            for disc in self.__discs:
                self._tracks_widget_left[disc.number].update_playing(
                    App().player.current_track.id)
                self._tracks_widget_right[disc.number].update_playing(
                    App().player.current_track.id)
        except Exception as e:
            Logger.error("TrackView::set_playing_indicator(): %s" % e)

    def update_duration(self, track_id):
        """
            Update track duration
            @param track_id as int
        """
        try:
            for disc in self.__discs:
                number = disc.number
                self._tracks_widget_left[number].update_duration(track_id)
                self._tracks_widget_right[number].update_duration(track_id)
        except Exception as e:
            Logger.error("TrackView::update_duration(): %s" % e)

    def populate(self):
        """
            Populate tracks
            @thread safe
        """
        if self._responsive_widget is None:
            if self._view_type & ViewType.DND:
                self.connect("key-press-event", self.__on_key_press_event)
            self._responsive_widget = Gtk.Grid()
            self._responsive_widget.set_column_spacing(20)
            self._responsive_widget.connect("size-allocate",
                                            self.__on_size_allocate)
            self._responsive_widget.set_column_homogeneous(True)
            self._responsive_widget.set_property("valign", Gtk.Align.START)

            self._tracks_widget_left = {}
            self._tracks_widget_right = {}

            if self._view_type & (ViewType.DND | ViewType.SEARCH):
                self.__discs = [self._album.one_disc]
            else:
                self.__discs = self._album.discs
            self.__discs_to_load = list(self.__discs)
            for disc in self.__discs:
                self.__add_disc_container(disc.number)
        if self.__discs_to_load:
            disc = self.__discs_to_load.pop(0)
            disc_number = disc.number
            tracks = get_position_list(disc.tracks, 0)
            if self._view_type & ViewType.TWO_COLUMNS:
                mid_tracks = int(0.5 + len(tracks) / 2)
                widgets = {self._tracks_widget_left[disc_number]:
                           tracks[:mid_tracks],
                           self._tracks_widget_right[disc_number]:
                           tracks[mid_tracks:]}
                self.__add_tracks(OrderedDict(widgets), disc_number)
            else:
                widgets = {self._tracks_widget_left[disc_number]: tracks}
                self.__add_tracks(OrderedDict(widgets), disc_number)

    def append_rows(self, tracks):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
        """
        position = len(self.children)
        previous_row = None if position == 1 else self.children[-1]
        widgets = {self._tracks_widget_left[0]:
                   get_position_list(tracks, position)}
        self.__add_tracks(OrderedDict(widgets), 0, previous_row)

    def prepend_rows(self, tracks):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
        """
        widgets = {self._tracks_widget_left[0]:
                   get_position_list(tracks, 0)}
        self.__add_tracks(OrderedDict(widgets), 0)

    def rows_animation(self, x, y, widget):
        """
            Show animation to help user dnd
            @param x as int
            @param y as int
            @param widget as Gtk.Widget
        """
        if self._responsive_widget is None:
            return None
        for row in self.children:
            coordinates = row.translate_coordinates(widget, 0, 0)
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
            if y <= row_y + row_height / 2:
                row.get_style_context().add_class("drag-up")
                return row
            elif y >= row_y + row_height / 2:
                row.get_style_context().add_class("drag-down")
                return row
        return None

    def get_current_ordinate(self, parent):
        """
            If current track in widget, return it ordinate,
            @param parent widget as Gtk.Widget
            @return y as int
        """
        for child in self.children:
            if child.id == App().player.current_track.id:
                return child.translate_coordinates(parent, 0, 0)[1]
        return None

    def stop(self):
        """
            Stop loading
        """
        self.__cancellable.cancel()

    def get_populated(self):
        """
            Return True if populated
            @return bool
        """
        return self.__populated

    @property
    def children(self):
        """
            Return all rows
            @return [Gtk.ListBoxRow]
        """
        rows = []
        for disc in self.__discs:
            for widget in [
                self._tracks_widget_left[disc.number],
                self._tracks_widget_right[disc.number]
            ]:
                rows += widget.get_children()
        return rows

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        boxes = []
        for widget in self._tracks_widget_left.values():
            boxes.append(widget)
        for widget in self._tracks_widget_right.values():
            boxes.append(widget)
        return boxes

    @property
    def discs(self):
        """
            Get widget discs
            @return [Discs]
        """
        return self.__discs

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return self.get_populated()

#######################
# PROTECTED           #
#######################
    def _on_album_updated(self, scanner, album_id):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album_id as int
        """
        if self._album.id != album_id:
            return
        removed = False
        for dic in [self._tracks_widget_left, self._tracks_widget_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    if child.track.album.id == Type.NONE:
                        removed = True
        if removed:
            for dic in [self._tracks_widget_left, self._tracks_widget_right]:
                for widget in dic.values():
                    for child in widget.get_children():
                        child.destroy()
            self.__discs = list(self.__discs)
            self.__set_duration()
            self.populate()

    def _on_tracks_populated(self, disc_number):
        """
            Tracks populated
            @param disc_number
        """
        pass

#######################
# PRIVATE             #
#######################
    def __linking(self):
        """
            Handle linking between left and right
            Only used with ViewType.DND
        """
        if len(self._tracks_widget_left[0]) == 0 or\
                len(self._tracks_widget_right[0]) == 0:
            return
        last_left = self._tracks_widget_left[0].get_children()[-1]
        first_right = self._tracks_widget_right[0].get_children()[0]
        last_left.set_next_row(first_right)
        first_right.set_previous_row(last_left)

    def __add_disc_container(self, disc_number):
        """
            Add disc container to box
            @param disc_number as int
        """
        self._tracks_widget_left[disc_number] = TracksWidget()
        self._tracks_widget_right[disc_number] = TracksWidget()
        self._tracks_widget_left[disc_number].connect("activated",
                                                      self.__on_activated)
        self._tracks_widget_right[disc_number].connect("activated",
                                                       self.__on_activated)

    def __add_tracks(self, widgets, disc_number, previous_row=None):
        """
            Add tracks for to tracks widget
            @param widgets as OrderedDict
            @param disc number as int
            @param previous_row as TrackRow
        """
        if self.__cancellable.is_cancelled():
            return

        widget = next(iter(widgets))
        widgets.move_to_end(widget)
        tracks = widgets[widget]

        if not tracks:
            if len(self.__discs_to_load) == 0:
                self.__populated = True
            self._on_tracks_populated(disc_number)
            self._tracks_widget_left[disc_number].show()
            self._tracks_widget_right[disc_number].show()
            if self._view_type & ViewType.DND:
                self.__linking()
            return

        (track, position) = tracks.pop(0)
        if not App().settings.get_value("show-tag-tracknumber"):
            track.set_number(position + 1)
        row = TrackRow(track, self._album.artist_ids, self._view_type)
        if self._view_type & ViewType.DND:
            row.set_previous_row(previous_row)
            if previous_row is not None:
                previous_row.set_next_row(row)
            row.connect("destroy", self.__on_row_destroy)
            row.connect("insert-track", self.__on_insert_track)
            row.connect("insert-album", self.__on_insert_album)
            row.connect("remove-track", self.__on_remove_track)
            row.connect("do-selection", self.__on_do_selection)
        row.show()
        widget.insert(row, position)
        GLib.idle_add(self.__add_tracks, widgets, disc_number, row)

    def __get_split_tracks(self, row, down):
        """
            Get tracks for row split
            @param row as Row
            @param down as bool
            @return [tracks]
        """
        # Create a new album with reminding tracks
        if down:
            split_tracks = []
        else:
            if row.previous_row is not None:
                row.previous_row.set_next_row(None)
            split_tracks = [Track(row.track.id)]
        # First get tracks
        r = row
        while r.next_row is not None:
            split_tracks.append(Track(r.next_row.track.id))
            r = r.next_row
        return split_tracks

    def __destroy_split(self, row, down):
        """
            Destroy rows not needed after split
            @param row as Row
            @param down as bool
        """
        if down:
            r = row.next_row
        else:
            r = row
        while r is not None:
            r.track.album.remove_track(r.track)
            r.destroy()
            r = r.next_row
        if down:
            row.set_next_row(None)

    def __handle_size_allocate(self, allocation):
        """
            Change box max/min children
            @param allocation as Gtk.Allocation
        """
        self.__allocation_timeout_id = None
        # We need an initial orientation but we only need to follow allocation
        # in TWO_COLUMNS mode
        if allocation.width != 1 and\
                not self._view_type & ViewType.TWO_COLUMNS and\
                self._orientation is not None:
            return
        if self._width == allocation.width:
            return
        self._width = allocation.width
        redraw = False
        # We want vertical orientation
        # when not enought place for cover or tracks
        if allocation.width < Sizing.BIG:
            orientation = Gtk.Orientation.VERTICAL
        else:
            orientation = Gtk.Orientation.HORIZONTAL
        if orientation != self._orientation:
            self._orientation = orientation
            redraw = True

        if redraw:
            for child in self._responsive_widget.get_children():
                self._responsive_widget.remove(child)
            idx = 0
            # Vertical
            ##########################
            #  --------Label-------- #
            #  |     Column 1      | #
            #  |     Column 2      | #
            ##########################
            # Horizontal
            ###########################
            # ---------Label--------- #
            # | Column 1 | Column 2 | #
            ###########################
            for disc in self.__discs:
                if not disc.tracks:
                    continue
                show_label = len(self.__discs) > 1
                disc_names = self._album.disc_names(disc.number)
                if show_label or disc_names:
                    if disc_names:
                        disc_text = ", ".join(disc_names)
                    elif show_label:
                        disc_text = _("Disc %s") % disc.number
                    label = Gtk.Label.new()
                    label.set_ellipsize(Pango.EllipsizeMode.END)
                    label.set_text(disc_text)
                    label.set_property("halign", Gtk.Align.START)
                    label.get_style_context().add_class("dim-label")
                    label.show()
                    eventbox = Gtk.EventBox()
                    eventbox.connect("realize", on_realize)
                    eventbox.set_tooltip_text(_("Play"))
                    eventbox.connect("button-press-event",
                                     self.__on_disc_button_press_event,
                                     disc)
                    eventbox.add(label)
                    eventbox.show()
                    if orientation == Gtk.Orientation.VERTICAL:
                        self._responsive_widget.attach(eventbox, 0, idx, 1, 1)
                    else:
                        self._responsive_widget.attach(eventbox, 0, idx, 2, 1)
                    idx += 1
                if orientation == Gtk.Orientation.VERTICAL:
                    self._responsive_widget.attach(
                              self._tracks_widget_left[disc.number],
                              0, idx, 2, 1)
                    idx += 1
                else:
                    self._responsive_widget.attach(
                              self._tracks_widget_left[disc.number],
                              0, idx, 1, 1)
                if self._view_type & ViewType.TWO_COLUMNS:
                    if orientation == Gtk.Orientation.VERTICAL:
                        self._responsive_widget.attach(
                                   self._tracks_widget_right[disc.number],
                                   0, idx, 2, 1)
                    else:
                        self._responsive_widget.attach(
                                   self._tracks_widget_right[disc.number],
                                   1, idx, 1, 1)
                idx += 1

    def __on_row_destroy(self, row):
        """
            Destroy self if no more row
            @param row as Row
        """
        contain_children = False
        for box in self.boxes:
            if box.get_children():
                contain_children = True
                break
        if not contain_children:
            self.destroy()

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

    def __on_activated(self, widget, track):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track as Track
        """
        tracks = []
        for child in self.children:
            tracks.append(child.track)
            child.set_state_flags(Gtk.StateFlags.NORMAL, True)
        # Do not update album list if in party or album already available
        if not App().player.is_party and\
                not App().player.track_in_playback(track):
            album = self._album.clone(True)
            album.set_tracks(tracks)
            if not App().settings.get_value("append-albums"):
                App().player.clear_albums()
            App().player.add_album(album)
            App().player.load(album.get_track(track.id))
        else:
            App().player.load(track)

    def __on_insert_track(self, row, new_track_id, down):
        """
            Insert a new row at position
            @param row as PlaylistRow
            @param new_track_id as int
            @param down as bool
        """
        track = Track(new_track_id)
        # If same album, add track to album
        if track.album.id == row.track.album.id:
            position = self.children.index(row)
            new_row = TrackRow(track, track.album.artist_ids, self._view_type)
            new_row.connect("destroy", self.__on_row_destroy)
            new_row.connect("insert-track", self.__on_insert_track)
            new_row.connect("insert-album", self.__on_insert_album)
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
            row.get_parent().insert(new_row, position)
            row.track.album.insert_track(track, position)
            if new_row.previous_row is not None and\
                    new_row.previous_row.track.id ==\
                    App().player.current_track.id:
                App().player.set_next()
                App().player.set_prev()
        # Else, we need to insert a new album with the track
        else:
            # Backup album as __destroy_split() will unset it
            album = row.track.album
            split_album = Album(album.id)
            split_tracks = self.__get_split_tracks(row, down)
            # Create new album
            track.album.set_tracks([track])
            # We use DNDRow because we know that if tracks are DND
            # we are DND. Little hack
            if len(self.children) == len(split_tracks):
                if self.previous_row is not None:
                    album = self.previous_row.album
                else:
                    album = Album()
            elif not split_tracks:
                if self.next_row is not None:
                    album = self.next_row.album
                else:
                    album = Album()
            if album.id == track.album.id:
                track.set_album(album)
                if down:
                    self.next_row.prepend_rows([track])
                else:
                    self.previous_row.append_rows([track])
            else:
                self.emit("insert-album-after",
                          album,
                          track.album)
            # Create split album
            if split_tracks:
                split_album.set_tracks(split_tracks)
                if album.id == track.album.id:
                    self.emit("insert-album-after", album, split_album)
                else:
                    self.emit("insert-album-after", track.album, split_album)
                self.__destroy_split(row, down)

    def __on_remove_track(self, row):
        """
            Remove track from album
            @param row as PlaylistRow
            @param position as int
        """
        empty = row.track.album.remove_track(row.track)
        if empty:
            App().player.remove_album(row.track.album)
        if row.track.id == App().player.current_track.id:
            App().player.set_next()
            App().player.set_prev()
        if row.previous_row is None:
            if row.next_row is not None:
                row.next_row.set_previous_row(None)
        elif row.next_row is None:
            if row.previous_row is not None:
                row.previous_row.set_next_row(None)
        else:
            if row.next_row is not None:
                row.next_row.set_previous_row(row.previous_row)
            if row.previous_row is not None:
                row.previous_row.set_next_row(row.next_row)
            if row.previous_row.track.id == App().player.current_track.id:
                App().player.set_next()
                App().player.set_prev()

    def __on_insert_album(self, row, new_album_id, track_ids, down):
        """
            Insert a new row at position
            @param row as Row
            @param new_album_id as int
            @param track_ids as int
            @param down as bool
        """
        # Backup album as __destroy_split() will unset it
        album = row.track.album
        new_album = Album(new_album_id)
        tracks = [Track(track_id) for track_id in track_ids]
        new_album.set_tracks(tracks)
        split_album = Album(row.track.album.id)
        split_tracks = self.__get_split_tracks(row, down)
        split_album.set_tracks(split_tracks)
        self.emit("insert-album-after", album, new_album)
        self.emit("insert-album-after", new_album, split_album)
        self.__destroy_split(row, down)

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

    def __on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__allocation_timeout_id is not None:
            GLib.source_remove(self.__allocation_timeout_id)
        self.__allocation_timeout_id = GLib.idle_add(
            self.__handle_size_allocate, allocation)

    def __on_disc_button_press_event(self, button, event, disc):
        """
            Add disc to playback
            @param button as Gtk.Button
            @param event as Gdk.ButtonEvent
            @param disc as Disc
        """
        album = Album(disc.album.id)
        album.set_tracks(disc.tracks)
        App().player.play_album(album)
