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

from gi.repository import GLib, Gst, Gtk

from lollypop.objects_radio import Radio
from lollypop.define import App, StorageType, MARGIN_SMALL
from lollypop.utils import seconds_to_string
from lollypop.helper_signals import SignalsHelper, signals


class ProgressPlayerWidget(Gtk.Box, SignalsHelper):
    """
        Progress widget synced with player state
    """

    @signals
    def __init__(self):
        """
            Init box
        """
        Gtk.Box.__init__(self)
        # Prevent updating progress while seeking
        self.__seeking = False
        # Update pogress position
        self.__timeout_id = None
        self.__time_label = Gtk.Label.new()
        self.__time_label.show()
        self.__time_label.get_style_context().add_class("monospace")
        self.__progress = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, None)
        self.__progress.show()
        self.__progress.set_sensitive(False)
        self.__progress.set_hexpand(True)
        self.__progress.set_draw_value(False)
        self.__progress.connect("change-value", self.__on_change_value)
        self.__multi_press = Gtk.GestureMultiPress.new(self.__progress)
        self.__multi_press.set_propagation_phase(Gtk.PropagationPhase.TARGET)
        self.__multi_press.connect("pressed", self.__on_multi_pressed)
        self.__multi_press.connect("released", self.__on_multi_released)
        self.__multi_press.set_button(1)
        self.__event_controller = Gtk.EventControllerScroll.new(
            self.__progress, Gtk.EventControllerScrollFlags.BOTH_AXES)
        self.__event_controller.set_propagation_phase(
            Gtk.PropagationPhase.TARGET)
        self.__event_controller.connect("scroll", self.__on_scroll)
        self.__total_time_label = Gtk.Label.new()
        self.__total_time_label.show()
        self.__total_time_label.get_style_context().add_class("monospace")
        self.set_spacing(MARGIN_SMALL)
        self.pack_start(self.__time_label, False, False, 0)
        self.pack_start(self.__progress, False, True, 0)
        self.pack_start(self.__total_time_label, False, False, 0)
        self.connect("destroy", self.__on_destroy)
        return [
            (App().player, "current-changed", "_on_current_changed"),
            (App().player, "status-changed", "_on_status_changed"),
            (App().player, "duration-changed", "_on_duration_changed"),
            (App().player, "seeked", "_on_seeked")
        ]

    def update(self):
        """
            Update progress state
        """
        player = App().player
        self._on_current_changed(player)
        self._on_status_changed(player)

    def update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if not self.__seeking:
            if value is None and App().player.get_status() != Gst.State.PAUSED:
                value = App().player.position / Gst.SECOND
            if value is not None and value >= 0:
                self.__progress.set_value(value)
                self.__time_label.set_text(seconds_to_string(value))
        return True

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        """
            Update scale on current changed
            @param player as Player
        """
        style_context = self.__progress.get_style_context()
        style_context.remove_class("youtube-scale")
        if App().player.current_track.id is None:
            self.__total_time_label.set_text("")
            self.__time_label.set_text("")
            return

        self.__progress.set_value(0.0)
        self.__time_label.set_text("0:00")
        if isinstance(App().player.current_track, Radio):
            self.__progress.set_sensitive(False)
        else:
            if not App().player.current_track.storage_type &\
                    StorageType.COLLECTION:
                style_context.add_class("youtube-scale")
            self.__progress.set_sensitive(True)
            self.__progress.set_range(0.0, App().player.current_track.duration)
            self.__total_time_label.set_text(
                seconds_to_string(App().player.current_track.duration))

    def _on_duration_changed(self, player, track_id):
        """
            Update duration
            @param player as Player
            @param track_id as int
        """
        if track_id == player.current_track.id:
            duration = player.current_track.duration
            self.__progress.set_range(0.0, duration)
            self.__total_time_label.set_text(seconds_to_string(duration))

    def _on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        if player.is_playing:
            if self.__timeout_id is None:
                self.__timeout_id = GLib.timeout_add(1000,
                                                     self.update_position)
        else:
            if self.__timeout_id is not None:
                GLib.source_remove(self.__timeout_id)
                self.__timeout_id = None

    def _on_seeked(self, player, position):
        """
            Update position
            @param position as int
        """
        self.update_position(position)

#######################
# PRIVATE             #
#######################
    def __on_change_value(self, progress, scroll_type, value):
        """
            Update label
            @param progress as Gtk.Scale
            @param scroll_type as Gtk.ScrollType
            @param value as float
        """
        self.__time_label.set_text(seconds_to_string(value))

    def __on_multi_pressed(self, gesture, n_press, x, y):
        """
            On press, mark player as seeking
            @param gesture as Gtk.Gesture
            @param n_press as int
            @param x as int
            @param y as int
        """
        self.__seeking = True

    def __on_multi_released(self, gesture, n_press, x, y):
        """
            Callback for scale release button
            @param gesture as Gtk.Gesture
            @param n_press as int
            @param x as int
            @param y as int
        """
        if n_press != 1:
            return
        value = self.__progress.get_value()
        App().player.seek(value)
        self.__seeking = False
        self.update_position(value)

    def __on_scroll(self, event_controler, x, y):
        """
            Seek forward or backward
            @param event_controller as Gtk.EventControllerScroll
            @param x as int
            @param y as int
        """
        if x == 0:
            diff = -y
        else:
            diff = -x
        if App().player.is_playing:
            position = App().player.position / Gst.SECOND
            seek = position + diff * 5
            seek = max(min(App().player.current_track.duration - 2, seek), 0)
            App().player.seek(seek)
            self.update_position(seek)

    def __on_destroy(self, widget):
        """
            Stop timeout
            @param widget as Gtk.Widget
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
