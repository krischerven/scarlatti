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
from locale import strcoll

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type, ViewType, SelectionListMask
from lollypop.widgets_playlist_rounded import PlaylistRoundedWidget
from lollypop.shown import ShownPlaylists
from lollypop.helper_signals import SignalsHelper, signals


class PlaylistsManagerView(FlowBoxView, SignalsHelper):
    """
        Show playlists in a FlowBox
    """

    @signals
    def __init__(self, view_type=ViewType.SCROLLED):
        """
            Init decade view
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type)
        self.__signal_id = None
        self._empty_icon_name = "emblem-documents-symbolic"
        self._new_button = Gtk.Button(_("New playlist"))
        self._new_button.connect("clicked", self.__on_new_button_clicked)
        self._new_button.set_property("halign", Gtk.Align.CENTER)
        self._new_button.set_hexpand(True)
        self._new_button.set_margin_top(5)
        self._new_button.show()
        self.insert_row(0)
        self.attach(self._new_button, 0, 0, 1, 1)
        self._widget_class = PlaylistRoundedWidget
        return [
                (App().playlists, "playlists-changed", "_on_playlist_changed")
        ]

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            items = [i[0] for i in ShownPlaylists.get()]
            items += App().playlists.get_ids()
            return items

        App().task_helper.run(load, callback=(on_load,))

    def add_value(self, item):
        """
            Insert item
            @param item as (int, str, str)
        """
        for child in self._box.get_children():
            if child.data == item[0]:
                return
        # Setup sort on insert
        self._box.set_sort_func(self.__sort_func)
        from lollypop.utils import get_font_height
        widget = PlaylistRoundedWidget(item[0],
                                       self._view_type,
                                       get_font_height())
        widget.populate()
        widget.show()
        self._box.insert(widget, -1)

    def remove_value(self, item_id):
        """
            Remove value
            @param item_id as int
        """
        for child in self._box.get_children():
            if child.data == item_id:
                child.destroy()
                break

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        view_type = self._view_type & ~self.view_sizing_mask
        return ({"view_type": view_type}, self.sidebar_id, position)

#######################
# PROTECTED           #
#######################
    def _add_items(self, playlist_ids, *args):
        """
            Add albums to the view
            Start lazy loading
            @param playlist_ids as [int]
        """
        self._remove_placeholder()
        FlowBoxView._add_items(self, playlist_ids, self._view_type)

    def _on_child_activated(self, flowbox, child):
        """
            Enter child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().window.container.show_view([Type.PLAYLISTS], child.data)

    def _on_secondary_press_gesture(self, x, y, event):
        """
            Show Context view for activated album
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        self._on_primary_long_gesture(x, y)

    def _on_primary_long_gesture(self, x, y):
        """
            Show Context view for activated album
            @param x as int
            @param y as int
        """
        child = self._box.get_child_at_pos(x, y)
        if child is None or child.artwork is None:
            return
        self.__popup_menu(child)

    def _on_playlist_changed(self, playlists, playlist_id):
        """
            Update view based on playlist_id status
            @param playlists as Playlists
            @param playlist_id as int
        """
        exists = playlists.exists(playlist_id)
        if exists:
            item = None
            for child in self._box.get_children():
                if child.data == playlist_id:
                    item = child
                    break
            if item is None:
                # Setup sort on insert
                self._box.set_sort_func(self.__sort_func)
                self._add_items([playlist_id])
            else:
                name = App().playlists.get_name(playlist_id)
                item.rename(name)
        else:
            for child in self._box.get_children():
                if child.data == playlist_id:
                    child.destroy()

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, child):
        """
            Popup menu for track
            @param child as PlaylistRoundedWidget
        """
        from lollypop.menu_selectionlist import SelectionListMenu
        from lollypop.widgets_utils import Popover
        menu = SelectionListMenu(self,
                                 child.data,
                                 SelectionListMask.PLAYLISTS)
        popover = Popover()
        popover.bind_model(menu, None)
        popover.set_relative_to(child.artwork)
        popover.popup()

    def __sort_func(self, widget1, widget2):
        """
            Sort function
            @param widget1 as PlaylistRoundedWidget
            @param widget2 as PlaylistRoundedWidget
        """
        # Static vs static
        if widget1.data < 0 and widget2.data < 0:
            return widget1.data < widget2.data
        # Static entries always on top
        elif widget2.data < 0:
            return True
        # Static entries always on top
        if widget1.data < 0:
            return False
        # String comparaison for non static
        else:
            return strcoll(widget1.name, widget2.name)

    def __on_new_button_clicked(self, button):
        """
            Add a new playlist
            @param button as Gtk.Button
        """
        App().playlists.add(App().playlists.get_new_name())


class PlaylistsManagerDeviceView(PlaylistsManagerView):
    """
        Show playlists in a FlowBox
    """

    def __init__(self, index, view_type=ViewType.SCROLLED):
        """
            Init decade view
            @param index as int
            @param view_type as ViewType
        """
        PlaylistsManagerView.__init__(self, view_type)
        self.__index = index
        self._new_button.hide()

    def populate(self):
        """
            Populate items
            @param items
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            items = App().playlists.get_synced_ids(0)
            items += App().playlists.get_synced_ids(self.__index)
            return items

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        return None
