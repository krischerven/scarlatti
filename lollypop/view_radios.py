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

from lollypop.define import App, Type, ViewType
from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_radio import RadioWidget
from lollypop.pop_tunein import TuneinPopover
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.utils import get_icon_name, get_network_available


class RadiosView(FlowBoxView, ViewController):
    """
        Show radios flow box
    """

    def __init__(self, view_type=ViewType.SCROLLED):
        """
            Init view
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.RADIO)
        self._widget_class = RadioWidget
        self._empty_icon_name = get_icon_name(Type.RADIOS)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadiosView.ui")
        builder.connect_signals(self)
        self.insert_row(0)
        self.attach(builder.get_object("widget"), 0, 0, 1, 1)
        self.__pop_tunein = None
        if not get_network_available("TUNEIN"):
            builder.get_object("search_btn").hide()

    def populate(self):
        """
            Add radio widgets
            @param radio_ids as [int]
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            return App().radios.get_ids()

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, {}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        return ({"view_type": self._view_type}, {"radio_ids": self._items},
                self._sidebar_id, position)

#######################
# PROTECTED           #
#######################
    def _add_items(self, radio_ids):
        """
            Add radios to the view
            Start lazy loading
            @param radio ids as [int]
        """
        self._remove_placeholder()
        widget = FlowBoxView._add_items(self, radio_ids, self._view_type)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

    def _on_new_clicked(self, widget):
        """
            Show popover for adding a new radio
            @param widget as Gtk.Widget
        """
        from lollypop.pop_radio import RadioPopover
        popover = RadioPopover(None, App().radios)
        popover.set_relative_to(widget)
        popover.popup()

    def _on_search_clicked(self, widget):
        """
            Show popover for searching radios
            @param widget as Gtk.Widget
        """
        if self.__pop_tunein is None:
            self.__pop_tunein = TuneinPopover()
            self.__pop_tunein.populate()
        self.__pop_tunein.set_relative_to(widget)
        self.__pop_tunein.popup()

    def _on_artwork_changed(self, artwork, name):
        """
            Update children artwork if matching name
            @param artwork as Artwork
            @param name as str
        """
        for child in self._box.get_children():
            if name == child.name:
                child.set_artwork()

    def _on_map(self, widget):
        """
            Set active ids
        """
        FlowBoxView._on_map(self, widget)
        self.__signal_id = App().radios.connect("radio-changed",
                                                self.__on_radio_changed)

    def _on_unmap(self, widget):
        """
            Destroy popover
            @param widget as Gtk.Widget
        """
        FlowBoxView._on_unmap(self, widget)
        if self.__signal_id is not None:
            App().radios.disconnect(self.__signal_id)
            self.__signal_id = None
        if self.__pop_tunein is not None:
            self.__pop_tunein.destroy()
            self.__pop_tunein = None

#######################
# PRIVATE             #
#######################
    def __on_radio_changed(self, radios, radio_id):
        """
            Update view based on radio_id status
            @param radios as Radios
            @param radio_id as int
        """
        exists = radios.exists(radio_id)
        if exists:
            item = None
            for child in self._box.get_children():
                if child.track.id == radio_id:
                    item = child
                    break
            if item is None:
                self._add_items([radio_id])
            else:
                name = App().radios.get_name(radio_id)
                item.rename(name)
        else:
            for child in self._box.get_children():
                if child.track.id == radio_id:
                    child.destroy()
