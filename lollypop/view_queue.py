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

from lollypop.define import App, ViewType, MARGIN, MARGIN_SMALL
from lollypop.objects_track import Track
from lollypop.view import View
from lollypop.widgets_row_queue import QueueRow


class QueueView(View):
    """
        View showing queue
    """

    def __init__(self, view_type=ViewType.DEFAULT):
        """
            Init Popover
            @param view_type as ViewType
        """
        View.__init__(self)
        self.__view_type = view_type
        self.__last_drag_id = None
        self.__stop = False
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/QueuePopover.ui")
        builder.connect_signals(self)

        self.__clear_button = builder.get_object("clear-button")

        self.__view = Gtk.ListBox()
        self.__view.set_margin_start(MARGIN_SMALL)
        self.__view.set_margin_end(MARGIN)
        self.__view.get_style_context().add_class("trackswidget")
        self.__view.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__view.set_activate_on_single_click(True)
        self.__view.connect("row-activated", self.__on_row_activated)
        self.__view.show()
        self.insert_row(0)
        self.attach(builder.get_object("widget"), 0, 0, 1, 1)
        self._viewport.add(self.__view)
        self._viewport.set_vexpand(True)
        self.add(self._scrolled)

    def populate(self):
        """
            Populate widget with queue rows
        """
        if App().player.queue:
            self.__clear_button.set_sensitive(True)
        self.__add_items(list(App().player.queue))

    @property
    def args(self):
        """
            Get default args for __class__ and populate()
            @return ({}, {})
        """
        return ({"view_type": self._view_type}, {})

#######################
# PROTECTED           #
#######################
    def _on_button_clicked(self, widget):
        """
            Clear queue
            @param widget as Gtk.Button
        """
        self.__stop = True
        self.__clear(True)
        self.hide()
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.popdown()

#######################
# PRIVATE             #
#######################
    def __clear(self, clear_queue=False):
        """
            Clear the view
        """
        for child in self.__view.get_children():
            child.destroy()
        if clear_queue:
            App().player.clear_queue()

    def __add_items(self, items, previous_row=None):
        """
            Add items to the view
            @param item ids as [int]
            @param previous_row as QueueRow
        """
        if items and not self.__stop:
            track_id = items.pop(0)
            row = self.__row_for_track_id(track_id)
            row.set_previous_row(previous_row)
            if previous_row is not None:
                previous_row.set_next_row(row)
            self.__view.add(row)
            GLib.idle_add(self.__add_items, items, row)

    def __row_for_track_id(self, track_id):
        """
            Get a row for track id
            @param track_id as int
        """
        row = QueueRow(Track(track_id), self.__view_type)
        row.connect("insert-track", self.__on_insert_track)
        row.connect("remove-track", self.__on_remove_track)
        return row

    def __on_map(self, widget):
        """
            Set initial state and connect signals
            @param widget as Gtk.Widget
        """
        window_size = App().window.get_size()
        height = window_size[1]
        width = min(500, window_size[0])
        self.set_size_request(width, height * 0.7)
        self._signal_id1 = App().player.connect("current-changed",
                                                self.__on_current_changed)

    def __on_unmap(self, widget):
        """
            Disconnect signals and stop loading
            @param widget as Gtk.Widget
        """
        self.__stop = True
        if self._signal_id1 is not None:
            App().player.disconnect(self._signal_id1)
            self._signal_id1 = None

    def __on_current_changed(self, player):
        """
            Pop first item in queue if it"s current track id
            @param player object
        """
        if len(self.__view.get_children()) > 0:
            row = self.__view.get_children()[0]
            if row.track.id == player.current_track.id:
                row.destroy()

    def __on_child_destroyed(self, row):
        """
            Check clear button aspect
            @param row as QueueRow
        """
        self.__clear_button.set_sensitive(len(self.__view.get_children()) != 0)

    def __on_row_activated(self, widget, row):
        """
            Play item
            @param widget as Gtk.ListBox
            @param row as QueueRow
        """
        App().player.load(row.track)
        GLib.idle_add(row.destroy)

    def __on_insert_track(self, row, new_track_id, down):
        """
            Insert a new row at position
            @param row as PlaylistRow
            @param new_track_id as int
            @param down as bool
        """
        self.__last_drag_id = new_track_id
        position = self.__view.get_children().index(row)
        new_row = self.__row_for_track_id(new_track_id)
        new_row.show()
        if down:
            position += 1
        self.__view.insert(new_row, position)
        App().player.insert_in_queue(new_row.track.id, position)
        if down:
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

    def __on_remove_track(self, row):
        """
            Remove row's track
            @param row as PlaylistRow
        """
        if row.track.id != self.__last_drag_id:
            App().player.remove_from_queue(row.track.id)
        if row.previous_row is None:
            row.next_row.set_previous_row(None)
        elif row.next_row is None:
            row.previous_row.set_next_row(None)
        else:
            row.next_row.set_previous_row(row.previous_row)
            row.previous_row.set_next_row(row.next_row)
        self.__last_drag_id = None
