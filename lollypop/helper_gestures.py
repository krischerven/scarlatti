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

from gi.repository import Gtk


class GesturesHelper():
    """
        Helper for gesture on widgets
    """

    def __init__(self, widget):
        """
            Init helper
        """
        self.__long_press = Gtk.GestureLongPress.new(self._box)
        self.__long_press.connect("pressed", self.__on_long_pressed)
        self.__long_press.set_button(0)
        self.__multi_press = Gtk.GestureMultiPress.new(self._box)
        self.__multi_press.connect("released", self.__on_multi_released)
        self.__multi_press.set_button(0)

#######################
# PROTECTED           #
#######################
    def _on_primary_long_press_gesture(self, x, y):
        pass

    def _on_secondary_long_press_gesture(self, x, y):
        pass

    def _on_primary_press_gesture(self, x, y, event):
        pass

    def _on_secondary_press_gesture(self, x, y, event):
        pass

#######################
# PRIVATE             #
#######################
    def __on_long_pressed(self, gesture, x, y):
        """
            Check pressed button
        """
        if gesture.get_current_button() == 1:
            self._on_primary_long_press_gesture(x, y)
        else:
            self._on_secondary_long_press_gesture(x, y)

    def __on_multi_released(self, gesture, n_press, x, y):
        """
            Check released button
        """
        sequence = gesture.get_current_sequence()
        event = gesture.get_last_event(sequence)
        if gesture.get_current_button() == 1:
            self._on_primary_press_gesture(x, y, event)
        else:
            self._on_secondary_press_gesture(x, y, event)
