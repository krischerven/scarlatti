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

from gettext import gettext as _

from lollypop.define import ArtSize, MARGIN, ViewType
from lollypop.utils import update_button, get_network_available
from lollypop.widgets_banner import BannerWidget


class RadiosBannerWidget(BannerWidget):
    """
        Banner for radios
    """

    def __init__(self, view_type):
        """
            Init banner
            @param view_type as ViewType
        """
        BannerWidget.__init__(self, view_type)
        self.__pop_tunein = None
        grid = Gtk.Grid()
        grid.set_property("valign", Gtk.Align.CENTER)
        grid.show()
        new_button = Gtk.Button.new_with_label(_("New radio"))
        new_button.connect("clicked", self.__on_new_button_clicked)
        new_button.set_property("halign", Gtk.Align.CENTER)
        new_button.get_style_context().add_class("menu-button-48")
        new_button.get_style_context().add_class("black-transparent")
        new_button.get_style_context().add_class("bold")
        new_button.set_hexpand(True)
        new_button.show()
        self.__tunein_button = Gtk.Button.new()
        image = Gtk.Image.new()
        image.show()
        self.__tunein_button.set_image(image)
        self.__tunein_button.show()
        self.__tunein_button.set_margin_end(MARGIN)
        self.__tunein_button.get_style_context().add_class("black-transparent")
        self.__tunein_button.connect("clicked",
                                     self.__on_tunein_button_clicked)
        grid.add(new_button)
        grid.add(self.__tunein_button)
        if not get_network_available("TUNEIN"):
            self.__tunein_button.hide()
        self._overlay.add_overlay(grid)
        self._overlay.set_overlay_pass_through(grid, True)
        self.connect("unmap", self.__on_unmap)

    def set_view_type(self, view_type):
        """
            Update view type
            @param view_type as ViewType
        """
        BannerWidget.set_view_type(self, view_type)
        if view_type & ViewType.MEDIUM:
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
        else:
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
        update_button(self.__tunein_button, style,
                      icon_size, "edit-find-symbolic")

    @property
    def height(self):
        """
            Get wanted height
            @return int
        """
        return ArtSize.SMALL

#######################
# PRIVATE             #
#######################
    def __on_unmap(self, widget):
        """
            Destroy popover
            @param widget as Gtk.Widget
        """
        if self.__pop_tunein is not None:
            self.__pop_tunein.destroy()
            self.__pop_tunein = None

    def __on_new_button_clicked(self, button):
        """
            Show RadioPopover
            @param button as Gtk.Button
        """
        from lollypop.pop_radio import RadioPopover
        popover = RadioPopover()
        popover.set_relative_to(button)
        popover.popup()

    def __on_tunein_button_clicked(self, button):
        """
            Show playlist menu
            @param button as Gtk.Button
        """
        if self.__pop_tunein is None:
            from lollypop.pop_tunein import TuneinPopover
            self.__pop_tunein = TuneinPopover()
            self.__pop_tunein.populate()
        self.__pop_tunein.set_relative_to(button)
        self.__pop_tunein.popup()
