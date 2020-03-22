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

from gi.repository import Gtk, GObject

from lollypop.utils import emit_signal
from lollypop.define import App


class ComboRow(Gtk.ListBoxRow):
    """
        A Row for combobox
    """

    def __init__(self, title):
        """
            Init widget
            @param title as str
        """
        Gtk.ListBoxRow.__init__(self)
        self.get_style_context().add_class("big-padding")
        self.__label = Gtk.Label.new(title)
        self.__label.show()
        self.__label.set_property("halign", Gtk.Align.START)
        self.add(self.__label)

    @property
    def title(self):
        """
            Get row title
            @return str
        """
        return self.__label.get_text()


class ComboBox(Gtk.MenuButton):
    """
        Implement one combobox to prevent this GTK bug:
        https://gitlab.gnome.org/World/lollypop/issues/2253
    """
    # Same signal than MenuWidget
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init widget
        """
        Gtk.MenuButton.__init__(self)
        grid = Gtk.Grid.new()
        grid.show()
        self.__label = Gtk.Label.new()
        self.__label.show()
        image = Gtk.Image.new_from_icon_name("pan-down-symbolic",
                                             Gtk.IconSize.BUTTON)
        image.show()
        grid.add(self.__label)
        grid.add(image)
        self.set_image(grid)
        self.__popover = Gtk.Popover.new()
        self.__popover.set_relative_to(self)
        height = max(300, App().window.get_allocated_height() / 2)
        self.__popover.set_size_request(-1, height)
        scrolled = Gtk.ScrolledWindow.new()
        scrolled.show()
        scrolled.set_policy(Gtk.PolicyType.NEVER,
                            Gtk.PolicyType.AUTOMATIC)
        self.__listbox = Gtk.ListBox.new()
        self.__listbox.show()
        self.__listbox.connect("row-activated", self.__on_row_activated)
        scrolled.add(self.__listbox)
        self.__popover.add(scrolled)
        self.set_popover(self.__popover)
        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        size_group.add_widget(self.__label)
        size_group.add_widget(self.__popover)

    def append(self, text):
        """
            Appends text to the list of strings stored in self
            @param text as str
        """
        row = ComboRow(text)
        row.show()
        self.__listbox.add(row)
        self.__label.set_text(text)

    def get_active_id(self):
        """
            Get active id
            @return str
        """
        return self.__listbox.get_selected_row().title

    def set_active_id(self, text):
        """
            Mark item_id as active
            @parma text as str
        """
        for row in self.__listbox.get_children():
            if row.title == text:
                self.__listbox.select_row(row)
                self.__label.set_text(text)
                break

    def __on_row_activated(self, listbox, row):
        """
            Close popover and change label
            @param listbox as Gtk.ListBox
            @param row as ComboRow
        """
        self.__label.set_text(row.title)
        self.__popover.popdown()
        emit_signal(self, "changed")
