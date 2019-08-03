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


class MotionContainer:
    """
        Manager sidebar state
    """

    def __init__(self):
        """
            Init container
        """
        self.__motion_ec = Gtk.EventControllerMotion.new(self)
        self.__motion_ec.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        self.__motion_ec.connect("motion", self.__on_motion_ec_motion)

############
# PRIVATE  #
############
    def __on_motion_ec_motion(self, motion_ec, x, y):
        """
            Update sidebar state based on current motion event
            @param motion_ec as Gtk.EventControllerMotion
            @param x as int
            @param y as int
        """
        if x < self._sidebar.get_allocated_width():
            self._sidebar.set_expanded(True)
        else:
            self._sidebar.set_expanded(False)
