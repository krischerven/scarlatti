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


class TypeAheadWidget(Gtk.Grid):
    """
        Special popover for find as type
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Grid.__init__(self)
        self.__left_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.__right_button = Gtk.Button.new_from_icon_name(
            "go-next-symbolic", Gtk.IconSize.BUTTON)
        self.__entry = Gtk.SearchEntry.new()
        self.__entry.set_size_request(200, -1)
        self.__left_button.show()
        self.__right_button.show()
        self.__entry.show()
        self.add(self.__left_button)
        self.add(self.__entry)
        self.add(self.__right_button)
        self.get_style_context().add_class("linked")
        self.get_style_context().add_class("padding")

    @property
    def left_button(self):
        """
            Get left button
            @return Gtk.Button
        """
        return self.__left_button

    @property
    def right_button(self):
        """
            Get right button
            @return Gtk.Button
        """
        return self.__right_button

    @property
    def entry(self):
        """
            Get popover entry
            @return Gtk.Entry
        """
        return self.__entry

#######################
# PRIVATE             #
#######################
