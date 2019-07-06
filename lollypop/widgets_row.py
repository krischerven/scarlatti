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

from gi.repository import Gtk, Pango, GLib, Gdk

from gettext import gettext as _

from lollypop.define import App, ViewType, MARGIN_SMALL, IndicatorType
from lollypop.widgets_indicator import IndicatorWidget
from lollypop.utils import seconds_to_string, on_query_tooltip


class Row(Gtk.ListBoxRow):
    """
        A row
    """

    def __init__(self, track, album_artist_ids, view_type):
        """
            Init row widgets
            @param track as Track
            @param album_artist_ids as [int]
            @param view_type as ViewType
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.ListBoxRow.__init__(self)
        self._view_type = view_type
        self._artists_label = None
        self._track = track
        self.__filtered = False
        self.__next_row = None
        self.__previous_row = None
        self._indicator = IndicatorWidget(self, view_type)
        self._row_widget = Gtk.EventBox()
        self._row_widget.connect("destroy", self._on_destroy)
        self.__gesture = Gtk.GestureLongPress.new(self._row_widget)
        self.__gesture.connect("pressed", self.__on_gesture_pressed)
        self.__gesture.connect("end", self.__on_gesture_end)
        # We want to get release event after gesture
        self.__gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.__gesture.set_button(0)
        self._grid = Gtk.Grid()
        self._grid.set_property("valign", Gtk.Align.CENTER)
        self._grid.set_column_spacing(5)
        self._row_widget.add(self._grid)
        self._title_label = Gtk.Label.new(
            GLib.markup_escape_text(self._track.name))
        self._title_label.set_use_markup(True)
        self._title_label.set_property("has-tooltip", True)
        self._title_label.connect("query-tooltip", on_query_tooltip)
        self._title_label.set_property("hexpand", True)
        self._title_label.set_property("halign", Gtk.Align.START)
        self._title_label.set_property("xalign", 0)
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        featuring_artist_ids = track.get_featuring_artist_ids(album_artist_ids)
        if featuring_artist_ids:
            artists = []
            for artist_id in featuring_artist_ids:
                artists.append(App().artists.get_name(artist_id))
            self._artists_label = Gtk.Label.new(GLib.markup_escape_text(
                ", ".join(artists)))
            self._artists_label.set_use_markup(True)
            self._artists_label.set_property("has-tooltip", True)
            self._artists_label.connect("query-tooltip", on_query_tooltip)
            self._artists_label.set_property("hexpand", True)
            self._artists_label.set_property("halign", Gtk.Align.END)
            self._artists_label.set_ellipsize(Pango.EllipsizeMode.END)
            self._artists_label.set_opacity(0.3)
            self._artists_label.set_margin_end(5)
            self._artists_label.show()
        duration = seconds_to_string(self._track.duration)
        self._duration_label = Gtk.Label.new(duration)
        self._duration_label.get_style_context().add_class("dim-label")
        self._num_label = Gtk.Label.new()
        self._num_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._num_label.set_width_chars(4)
        self._num_label.get_style_context().add_class("dim-label")
        self.update_number_label()
        self._grid.add(self._num_label)
        self._grid.add(self._title_label)
        if self._artists_label is not None:
            self._grid.add(self._artists_label)
        self._grid.add(self._duration_label)
        if self._view_type & ViewType.DND and\
                self._view_type & ViewType.POPOVER:
            self.__action_button = Gtk.Button.new_from_icon_name(
               "list-remove-symbolic",
               Gtk.IconSize.MENU)
            self.__action_button.set_tooltip_text(
               _("Remove from playback"))
        elif not self._view_type & (ViewType.POPOVER | ViewType.SEARCH):
            self.__action_button = Gtk.Button.new_from_icon_name(
               "view-more-symbolic",
               Gtk.IconSize.MENU)
        else:
            self.__action_button = None
        if self.__action_button is not None:
            self.__action_button.set_margin_end(MARGIN_SMALL)
            self.__action_button.connect("button-release-event",
                                         self.__on_action_button_release_event)
            self.__action_button.set_relief(Gtk.ReliefStyle.NONE)
            context = self.__action_button.get_style_context()
            context.add_class("menu-button")
            context.add_class("track-menu-button")
            self._grid.add(self.__action_button)
        else:
            self._duration_label.set_margin_end(MARGIN_SMALL)
        self.add(self._row_widget)
        self.set_indicator(self._get_indicator_type())
        self.update_duration()

    def update_duration(self):
        """
            Update track duration
        """
        self._track.reset("duration")
        duration = seconds_to_string(self._track.duration)
        self._duration_label.set_label(duration)

    def set_indicator(self, indicator_type=None):
        """
            Show indicator
            @param indicator_type as IndicatorType
        """
        if indicator_type is None:
            indicator_type = self._get_indicator_type()
        self._indicator.clear()
        if indicator_type & IndicatorType.LOADING:
            self._indicator.set_opacity(1)
            self._indicator.load()
        elif indicator_type & IndicatorType.PLAY:
            self._indicator.set_opacity(1)
            self.get_style_context().remove_class("trackrow")
            self.get_style_context().add_class("trackrowplaying")
            if indicator_type & IndicatorType.LOVED:
                self._indicator.play_loved()
            else:
                self._indicator.play()
        else:
            self.get_style_context().remove_class("trackrowplaying")
            self.get_style_context().add_class("trackrow")
            if indicator_type & IndicatorType.LOVED:
                self._indicator.set_opacity(1)
                self._indicator.loved()
            elif indicator_type & IndicatorType.SKIP:
                self._indicator.set_opacity(1)
                self._indicator.skip()
            else:
                self._indicator.set_opacity(0)

    def update_number_label(self):
        """
            Update position label for row
        """
        if App().player.track_in_queue(self._track):
            self._num_label.get_style_context().add_class("queued")
            pos = App().player.get_track_position(self._track.id)
            self._num_label.set_text(str(pos))
        elif self._track.number > 0:
            self._num_label.get_style_context().remove_class("queued")
            self._num_label.set_text(str(self._track.number))
        else:
            self._num_label.get_style_context().remove_class("queued")
            self._num_label.set_text("")

    def set_filtered(self, b):
        """
            Set widget filtered
            @param b as bool
            @return bool (should be shown)
        """
        self.__filtered = b
        if b:
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)
        else:
            self.set_state_flags(Gtk.StateFlags.VISITED, True)
        return True

    def set_next_row(self, row):
        """
            Set next row
            @param row as Row
        """
        self.__next_row = row

    def set_previous_row(self, row):
        """
            Set previous row
            @param row as Row
        """
        self.__previous_row = row

    @property
    def next_row(self):
        """
            Get next row
            @return row as Row
        """
        return self.__next_row

    @property
    def previous_row(self):
        """
            Get previous row
            @return row as Row
        """
        return self.__previous_row

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__filtered

    @property
    def row_widget(self):
        """
            Get row main widget
            @return Gtk.Widget
        """
        return self._row_widget

    @property
    def track(self):
        """
            Get row track
            @return Track
        """
        return self._track

#######################
# PROTECTED           #
#######################
    def _get_indicator_type(self):
        """
            Get indicator type for current row
            @return IndicatorType
        """
        indicator_type = IndicatorType.NONE
        if App().player.current_track.id == self._track.id:
            indicator_type |= IndicatorType.PLAY
        if self._track.loved == 1:
            indicator_type |= IndicatorType.LOVED
        elif self._track.loved == -1:
            indicator_type |= IndicatorType.SKIP
        return indicator_type

    def _get_menu(self):
        """
            Return TrackMenu
        """
        from lollypop.menu_objects import TrackMenu
        return TrackMenu(self._track)

    def _check_track(self):
        """
            Check track always valid, destroy if not
        """
        pass

    def _on_destroy(self, widget):
        pass

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, widget, xcoordinate=None, ycoordinate=None):
        """
            Popup menu for track
            @param widget as Gtk.Widget
            @param xcoordinate as int (or None)
            @param ycoordinate as int (or None)
        """
        def on_closed(widget):
            self.get_style_context().remove_class("track-menu-selected")
            self.set_indicator()
            # Event happens before Gio.Menu activation
            GLib.idle_add(self._check_track)

        from lollypop.pop_menu import TrackMenuPopover, RemoveMenuPopover
        if self.get_state_flags() & Gtk.StateFlags.SELECTED:
            # Get all selected rows
            rows = [self]
            r = self.previous_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    rows.append(r)
                r = r.previous_row
            r = self.next_row
            while r is not None:
                if r.get_state_flags() & Gtk.StateFlags.SELECTED:
                    rows.append(r)
                r = r.next_row
            popover = RemoveMenuPopover(rows)
        else:
            popover = TrackMenuPopover(self._track, self._get_menu())
        if xcoordinate is not None and ycoordinate is not None:
            rect = widget.get_allocation()
            rect.x = xcoordinate
            rect.y = ycoordinate
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
        popover.set_relative_to(widget)
        popover.connect("closed", on_closed)
        self.get_style_context().add_class("track-menu-selected")
        popover.popup()

    def __on_button_release_event(self, widget, event):
        """
            Handle button release event
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        widget.disconnect_by_func(self.__on_button_release_event)
        if event.state & Gdk.ModifierType.CONTROL_MASK and\
                self._view_type & ViewType.DND:
            if self.get_state_flags() & Gtk.StateFlags.SELECTED:
                self.set_state_flags(Gtk.StateFlags.NORMAL, True)
            else:
                self.set_state_flags(Gtk.StateFlags.SELECTED, True)
                self.grab_focus()
        elif event.state & Gdk.ModifierType.SHIFT_MASK and\
                self._view_type & ViewType.DND:
            self.emit("do-selection")
        elif event.button == 3:
            self.__popup_menu(self, event.x, event.y)
        elif event.button == 2:
            if self._track.id in App().player.queue:
                App().player.remove_from_queue(self._track.id)
            else:
                App().player.append_to_queue(self._track.id)
        elif event.state & Gdk.ModifierType.MOD1_MASK:
            App().player.clear_albums()
            App().player.reset_history()
            App().player.load(self._track)
        elif event.button == 1:
            self.activate()
            if self._track.is_web:
                self.set_indicator(IndicatorType.LOADING)
        return True

    def __on_gesture_pressed(self, gesture, x, y):
        """
            Show current track menu
            @param gesture as Gtk.GestureLongPress
            @param x as float
            @param y as float
        """
        if self._view_type & ViewType.DND and\
                self._view_type & ViewType.POPOVER:
            self._track.album.remove_track(self._track)
            self.destroy()
        else:
            self.__popup_menu(self, x, y)

    def __on_gesture_end(self, gesture, sequence):
        """
            Connect button release event
            Here because we only want this if a gesture was recognized
            This allow touch scrolling
        """
        self._row_widget.connect("button-release-event",
                                 self.__on_button_release_event)

    def __on_action_button_release_event(self, button, event):
        """
           Show row menu
            @param button as Gtk.Button
            @param event as Gdk.EventButton
        """
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            return
        if self._view_type & ViewType.DND and\
                self._view_type & ViewType.POPOVER:
            self._track.album.remove_track(self._track)
            self.destroy()
            App().player.set_next()
            App().player.set_prev()
        else:
            self.__popup_menu(button)
        return True
