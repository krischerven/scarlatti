# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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


class SearchPopover(Gtk.Popover):
    """
        Popover allowing user to search for tracks/albums
    """

    def __init__(self):
        """
            Init Popover
        """
        Gtk.Popover.__init__(self)
        self.__width = 0
        self.__search = ""
        self.set_position(Gtk.PositionType.BOTTOM)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)

    def set_search(self, search):
        """
            Set search text
            @param search as str
        """
        self.__search = search
        if self.get_child() is not None:
            self.get_child().set_search(search)

    def do_get_preferred_width(self):
        if self.__width == 0:
            return Gtk.Popover.do_get_preferred_width(self)
        else:
            return (self.__width, self.__width)

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_map(self, widget):
        """
            Set popover size
            @param widget as Gtk.Widget
        """
        search_view = App().window.container.get_view_search(self.__search)
        search_view.show()
        if search_view in App().window.container.stack.get_children():
            App().window.container.stack.remove(search_view)
        self.add(search_view)
        window_size = App().window.get_size()
        height = window_size[1]
        self.__width = min(500, window_size[0])
        self.set_size_request(self.__width, height * 0.7)

    def __on_unmap(self, widget):
        """
            Move widget inside container
        """
        search_view = self.get_child()
        search_view.hide()
        self.remove(search_view)
        App().window.container.stack.add(search_view)
