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

from lollypop.define import App


class MotionContainer:
    """
        Manager sidebar state
    """

    def __init__(self):
        """
            Init container
        """
        self.__event_controller = Gtk.EventControllerMotion.new(self)
        self.__event_controller.set_propagation_phase(
            Gtk.PropagationPhase.CAPTURE)
        self.__event_controller.connect(
            "motion", self.__on_event_controller_motion)

############
# PRIVATE  #
############
    def __on_event_controller_motion(self, event_controller, x, y):
        """
            Update sidebar state based on current motion event
            @param event_controller as Gtk.EventControllerMotion
            @param x as int
            @param y as int
        """
        if App().window.is_adaptive:
            return
        if x < self._sidebar.get_allocated_width():
            self._sidebar.set_expanded(True)
        else:
            self._sidebar.set_expanded(False)
