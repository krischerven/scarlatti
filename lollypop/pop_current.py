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

from lollypop.define import App, ViewType
from lollypop.widgets_utils import Popover


class CurrentPopover(Popover):
    """
        Popover showing current tracks
    """

    def __init__(self):
        """
            Init popover
        """
        Popover.__init__(self)
        # No DND until https://gitlab.gnome.org/GNOME/gtk/issues/2006 is fixed
        wayland = GLib.environ_getenv(GLib.get_environ(), "WAYLAND_DISPLAY")
        if wayland:
            view_type = ViewType.POPOVER
        else:
            view_type = ViewType.POPOVER | ViewType.DND
        self.__view = App().window.container.get_view_current(view_type)
        self.__view.show()
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.add(self.__view)

#######################
# PRIVATE             #
#######################
    def __on_map(self, widget):
        """
            Resize
            @param widget as Gtk.Widget
        """
        window_size = App().window.get_size()
        height = window_size[1]
        width = min(500, window_size[0])
        self.set_size_request(width, height * 0.7)

    def __on_unmap(self, widget):
        """
            Stop view
            @param widget as Gtk.Widget
        """
        self.__view.stop()
