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

from gi.repository import Gtk, Pango

from gettext import gettext as _

from lollypop.define import ArtSize, MARGIN, ViewType, Size
from lollypop.utils import get_network_available, popup_widget
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
        BannerWidget.__init__(self, view_type | ViewType.OVERLAY)
        self.__pop_tunein = None
        grid = Gtk.Grid()
        grid.set_property("valign", Gtk.Align.CENTER)
        grid.show()
        self.__title_label = Gtk.Label.new(
            "<b>" + _("Radios") + "</b>")
        self.__title_label.show()
        self.__title_label.set_use_markup(True)
        self.__title_label.set_hexpand(True)
        self.__title_label.get_style_context().add_class("dim-label")
        self.__title_label.set_property("halign", Gtk.Align.START)
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__new_button = Gtk.Button.new_from_icon_name(
            "document-new-symbolic", Gtk.IconSize.BUTTON)
        self.__new_button.connect("clicked", self.__on_new_button_clicked)
        self.__new_button.set_property("halign", Gtk.Align.CENTER)
        self.__new_button.get_style_context().add_class("banner-button")
        self.__new_button.show()
        self.__tunein_button = Gtk.Button.new_from_icon_name(
            "edit-find-symbolic", Gtk.IconSize.BUTTON)
        self.__tunein_button.show()
        self.__tunein_button.get_style_context().add_class("banner-button")
        self.__tunein_button.connect("clicked",
                                     self.__on_tunein_button_clicked)
        box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        box.show()
        box.get_style_context().add_class("linked")
        box.add(self.__new_button)
        box.add(self.__tunein_button)
        grid.add(self.__title_label)
        grid.add(box)
        grid.set_margin_start(MARGIN)
        grid.set_margin_end(MARGIN)
        if not get_network_available("TUNEIN"):
            self.__tunein_button.set_sensitive(False)
        self._overlay.add_overlay(grid)
        self._overlay.set_overlay_pass_through(grid, True)
        self.connect("unmap", self.__on_unmap)

    def update_for_width(self, width):
        """
            Update banner internals for width, call this before showing banner
            @param width as int
        """
        BannerWidget.update_for_width(self, width)
        self.__set_internal_size()

    @property
    def height(self):
        """
            Get wanted height
            @return int
        """
        return ArtSize.SMALL

#######################
# PROTECTED           #
#######################
    def _handle_width_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_width_allocate(self, allocation):
            self.__set_internal_size()

#######################
# PRIVATE             #
#######################
    def __set_internal_size(self):
        """
            Update font size
        """
        title_context = self.__title_label.get_style_context()
        for c in title_context.list_classes():
            title_context.remove_class(c)
        if self.width <= Size.MEDIUM:
            self.__title_label.get_style_context().add_class(
                "text-large")
        else:
            self.__title_label.get_style_context().add_class(
                "text-x-large")

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
        from lollypop.menu_radio import RadioMenu
        menu_widget = RadioMenu(None, self.view_type)
        menu_widget.show()
        popup_widget(menu_widget, button, None, None, button)

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
