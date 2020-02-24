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

from lollypop.define import App, Type, ViewType
from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_radio import RadioWidget
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.utils import get_icon_name
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.widgets_banner_radios import RadiosBannerWidget


class RadiosView(FlowBoxView, ViewController, SignalsHelper):
    """
        Show radios flow box
    """

    @signals_map
    def __init__(self, view_type=ViewType.SCROLLED):
        """
            Init view
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type |
                             ViewType.SCROLLED |
                             ViewType.OVERLAY)
        ViewController.__init__(self, ViewControllerType.RADIO)
        self._empty_icon_name = get_icon_name(Type.RADIOS)
        self.__banner = RadiosBannerWidget(self.view_type)
        self.__banner.show()
        self.add_widget(self._box, self.__banner)
        return [
                (App().radios, "radio-changed", "_on_radio_changed"),
                (App().player, "loading-changed", "_on_loading_changed")
        ]

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
            Get default args for __class__
            @return {}
        """
        return {"view_type": self.view_type & ~(ViewType.ADAPTIVE |
                                                ViewType.SMALL)}

#######################
# PROTECTED           #
#######################
    def _get_child(self, value):
        """
            Get a child for view
            @param value as object
            @return row as SelectionListRow
        """
        if self.destroyed:
            return None
        widget = RadioWidget(value, self.view_type, self.font_height)
        self._box.insert(widget, -1)
        widget.show()
        return widget

    def _get_menu_widget(self, child):
        """
            Get menu widget
            @param child as RadioWidget
            @return Gtk.Widget
        """
        from lollypop.menu_radio import RadioMenu
        return RadioMenu(child.data, self.view_type)

    def _on_child_activated(self, flowbox, child):
        """
            Navigate into child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().player.load(child.data)
        child.set_loading(True)

    def _on_artwork_changed(self, artwork, name):
        """
            Update children artwork if matching name
            @param artwork as Artwork
            @param name as str
        """
        for child in self._box.get_children():
            if name == child.name:
                child.set_artwork()

    def _on_loading_changed(self, player, status, track):
        """
            Stop loading for track child
        """
        for child in self.children:
            if child.data.id == track.id:
                child.set_loading(False)
                break

    def _on_radio_changed(self, radios, radio_id):
        """
            Update view based on radio_id status
            @param radios as Radios
            @param radio_id as int
        """
        exists = radios.exists(radio_id)
        if exists:
            item = None
            for child in self._box.get_children():
                if child.data.id == radio_id:
                    item = child
                    break
            if item is None:
                self.add_value(radio_id)
            else:
                name = App().radios.get_name(radio_id)
                item.rename(name)
        else:
            for child in self._box.get_children():
                if child.data.id == radio_id:
                    child.destroy()

#######################
# PRIVATE             #
#######################
