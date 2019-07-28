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

from gi.repository import GObject, Gtk, Gdk

from lollypop.define import App, ViewType, StorageType
from lollypop.utils import do_shift_selection, popup_widget
from lollypop.helper_signals import SignalsHelper, signals
from lollypop.helper_gestures import GesturesHelper


class TracksWidget(Gtk.ListBox, SignalsHelper, GesturesHelper):
    """
        A list of tracks
    """

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST,
                      None, (GObject.TYPE_PYOBJECT,))
    }

    @signals
    def __init__(self, view_type):
        """
            Init track widget
            @param view_type as ViewType
        """
        Gtk.ListBox.__init__(self)
        GesturesHelper.__init__(self, self)
        self.__view_type = view_type
        self.get_style_context().add_class("trackswidget")
        self.set_property("hexpand", True)
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        return {
            "init": [
                (App().player, "queue-changed", "_on_queue_changed")
            ]
        }

    def update_playing(self, track_id):
        """
            Update playing track
            @param track_id as int
        """
        for row in self.get_children():
            row.set_indicator()

    def update_duration(self, track_id):
        """
            Update duration for track id
            @param track_id as int
        """
        for row in self.get_children():
            if row.track.id == track_id:
                row.update_duration()

#######################
# PROTECTED           #
#######################
    def _on_queue_changed(self, *ignore):
        """
            Update all position labels
        """
        for row in self.get_children():
            row.update_number_label()

    def _on_primary_long_press_gesture(self, x, y):
        """
            Show row menu
            @param x as int
            @param y as int
        """
        row = self.get_row_at_y(y)
        if row is None:
            return
        self.__popup_menu(row, x, y)

    def _on_primary_press_gesture(self, x, y, event):
        """
            Activate current row
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        row = self.get_row_at_y(y)
        if row is None:
            return

        if event.state & Gdk.ModifierType.CONTROL_MASK and\
                self.__view_type & ViewType.DND:
            self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        elif event.state & Gdk.ModifierType.SHIFT_MASK and\
                self.__view_type & ViewType.DND:
            self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
            do_shift_selection(self, row)
        elif event.state & Gdk.ModifierType.MOD1_MASK:
            self.set_selection_mode(Gtk.SelectionMode.NONE)
            App().player.clear_albums()
            App().player.reset_history()
            App().player.load(row.track)
        else:
            self.set_selection_mode(Gtk.SelectionMode.NONE)
            self.emit("activated", row.track)

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
    def __popup_menu(self, row, x, y):
        """
            Popup menu for track
            @param row as Row
            @param x as int
            @param y as int
        """
        def on_closed(popover, row):
            row.unset_state_flags(Gtk.StateFlags.FOCUSED)
            row.set_indicator()

        if self.get_selected_rows():
            # from lollypop.pop_menu import RemoveMenuPopover
            # popover = RemoveMenuPopover(self.get_selected_rows())
            pass
        else:
            from lollypop.menu_objects import TrackMenu, TrackMenuExt
            from lollypop.widgets_menu import MenuBuilder
            menu = TrackMenu(row.track)
            menu_widget = MenuBuilder(menu)
            menu_widget.show()
            if not row.track.storage_type & StorageType.EPHEMERAL:
                menu_ext = TrackMenuExt(row.track)
                menu_ext.show()
                menu_widget.get_child_by_name("main").add(menu_ext)
            row.set_state_flags(Gtk.StateFlags.FOCUSED, True)
            popover = popup_widget(menu_widget, self, x, y)
            if popover is not None:
                popover.connect("closed", on_closed, row)
