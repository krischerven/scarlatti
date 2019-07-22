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

from gi.repository import GLib, Gst

from lollypop.objects_radio import Radio
from lollypop.define import App
from lollypop.utils import seconds_to_string


class ProgressController:
    """
        Progress controller (for toolbars)
    """

    def __init__(self):
        """
            Init progress controller (for toolbars)
        """
        # Prevent updating progress while seeking
        self.__seeking = False
        # Update pogress position
        self.__timeout_id = None
        self.connect("unmap", self.__on_unmap)
        self.signals_map = [
            (App().player, "seeked", "_on_seeked")
        ]

    def on_current_changed(self, player):
        """
            Update scale on current changed
            @param player as Player
        """
        style_context = self._progress.get_style_context()
        style_context.remove_class("youtube-scale")
        if player.current_track.id is None:
            self._progress.set_sensitive(False)
            self._total_time_label.set_text("")
            self._timelabel.set_text("")
            return

        self._progress.set_value(0.0)
        self._timelabel.set_text("0:00")
        if isinstance(player.current_track, Radio):
            self._progress.set_sensitive(False)
            self._progress.set_opacity(0)
            self._timelabel.set_opacity(0)
            self._total_time_label.set_opacity(0)
            self._progress.set_range(0.0, 0.0)
        else:
            if player.current_track.mtime <= 0:
                style_context.add_class("youtube-scale")
            self._progress.set_sensitive(True)
            self._progress.set_opacity(1)
            self._timelabel.set_opacity(1)
            self._total_time_label.set_opacity(1)
            self._progress.set_range(0.0, player.current_track.duration)
            self._total_time_label.set_text(
                seconds_to_string(player.current_track.duration))

    def on_duration_changed(self, player, track_id):
        """
            Update duration
            @param player as Player
            @param track_id as int
        """
        if track_id == player.current_track.id:
            duration = player.current_track.duration
            self._progress.set_range(0.0, duration)
            self._total_time_label.set_text(seconds_to_string(duration))

    def on_status_changed(self, player):
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

    def update_position(self, value=None):
        """
            Update progress bar position
            @param value as int
        """
        if not self.__seeking:
            if value is None and App().player.get_status() != Gst.State.PAUSED:
                value = App().player.position / Gst.SECOND
            if value is not None and value >= 0:
                self._progress.set_value(value)
                self._timelabel.set_text(seconds_to_string(value))
        return True

#######################
# PROTECTED           #
#######################
    def _update_state(self):
        """
            Update controller state volume vs progress
        """
        ProgressController.on_current_changed(self, App().player)
        if App().player.current_track.id is None:
            self._timelabel.set_text("")
            self._progress.set_value(0.0)
            self._progress.set_range(0.0, 0.0)
            self._progress.set_sensitive(False)
        else:
            self.update_position()

    def _on_progress_press_button(self, scale, event):
        """
            On press, mark player as seeking
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        self.__seeking = True

    def _on_progress_release_button(self, scale, event):
        """
            Callback for scale release button
            Seek player to scale value
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        if event.button != 1:
            return
        value = scale.get_value()
        App().player.seek(value)
        self.__seeking = False
        self.update_position(value)

    def _on_scroll_event(self, scale, event):
        """
            Seek forward or backward
            @param scale as Gtk.Scale
            @param event as Gdk.Event
        """
        (smooth, x, y) = event.get_scroll_deltas()
        if smooth and App().player.is_playing:
            position = App().player.position / Gst.SECOND
            if y >= 0:
                seek = position - 5
            elif y < 0:
                seek = position + 5
            if seek < 0:
                seek = 0
            if seek > App().player.current_track.duration:
                seek = App().player.current_track.duration - 2
            App().player.seek(seek)
            self.update_position(seek)

    def _on_seeked(self, player, position):
        """
            Update position
            @param position as int
        """
        self.update_position(position)

#######################
# PRIVATE             #
#######################
    def __on_unmap(self, widget):
        """
            Stop timeout
            @param widget as Gtk.Widget
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
