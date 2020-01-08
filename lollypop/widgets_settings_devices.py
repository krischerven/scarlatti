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

from gi.repository import Gtk, GLib, Pango


from lollypop.define import App


class DeviceRow(Gtk.ListBoxRow):
    """
        A device row
    """

    def __init__(self, name):
        """
            Init row
            @param name as str
        """
        Gtk.ListBoxRow.__init__(self)
        self.__name = name
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.show()
        label = Gtk.Label.new(name)
        label.set_property("halign", Gtk.Align.START)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.show()
        button = Gtk.Button.new_from_icon_name("user-trash-symbolic",
                                               Gtk.IconSize.BUTTON)
        button.connect("clicked", self.__on_button_clicked)
        button.get_style_context().add_class("menu-button")
        button.show()
        grid.add(label)
        grid.add(button)
        self.add(grid)

#######################
# PRIVATE             #
#######################
    def __on_button_clicked(self, button):
        """
            Remove device
            @param button as Gtk.Button
        """
        if button.get_image().get_style_context().has_class("red"):
            devices = list(App().settings.get_value("devices"))
            if self.__name in devices:
                index = devices.index(self.__name)
                devices[index] = ""
                App().settings.set_value("devices",
                                         GLib.Variant("as", devices))
                App().albums.remove_device(index + 1)
                App().playlists.remove_device(index + 1)
            self.destroy()
        else:
            button.get_image().get_style_context().add_class("red")


class DevicesSettingsWidget(Gtk.Bin):
    """
        Widget allowing user to manage known devices
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsDevices.ui")
        listbox = builder.get_object("listbox")
        self.add(builder.get_object("widget"))
        for device in App().settings.get_value("devices"):
            if device:
                row = DeviceRow(device)
                row.show()
                listbox.add(row)

#######################
# PRIVATE             #
#######################
