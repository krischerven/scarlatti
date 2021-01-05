# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, GObject

from lollypop.helper_gestures import GesturesHelper
from lollypop.utils import set_cursor_type


class Label(Gtk.EventBox):
    """
        A clickable label
    """

    __gsignals__ = {
        "clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init label
        """
        Gtk.EventBox.__init__(self)
        self.__label = Gtk.Label.new()
        self.__label.show()
        self.add(self.__label)
        self.__gesture = GesturesHelper(
            self, primary_press_callback=self._on_press)
        self.connect("realize", set_cursor_type)

    @property
    def widget(self):
        """
            Get Gtk.Label widget
            @return widget
        """
        return self.__label

#######################
# PROTECTED           #
#######################
    def _on_press(self, x, y, event):
        self.emit("clicked")
