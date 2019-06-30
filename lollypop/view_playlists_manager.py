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

from gettext import gettext as _
from locale import strcoll

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type, ViewType, SidebarContent
from lollypop.widgets_playlist_rounded import PlaylistRoundedWidget
from lollypop.shown import ShownPlaylists


class PlaylistsManagerView(FlowBoxView):
    """
        Show playlists in a FlowBox
    """

    def __init__(self, obj, view_type=ViewType.SCROLLED):
        """
            Init decade view
            @param obj as Track/Album
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type)
        self._empty_icon_name = "emblem-documents-symbolic"
        self.__obj = obj
        self.__signal_id = None
        if not view_type & ViewType.DEVICES:
            new_playlist_button = Gtk.Button(_("New playlist"))
            new_playlist_button.connect("clicked",
                                        self.__on_new_button_clicked)
            new_playlist_button.set_property("halign", Gtk.Align.CENTER)
            new_playlist_button.set_hexpand(True)
            new_playlist_button.set_margin_top(5)
            new_playlist_button.show()
            self.insert_row(0)
            self.attach(new_playlist_button, 0, 0, 1, 1)
        self._widget_class = PlaylistRoundedWidget

    def populate(self, items=None):
        """
            Populate items
            @param items
        """
        if self.__obj is not None:
            new_items = []
            for item in App().playlists.get_ids():
                if not App().playlists.get_smart(item):
                    new_items.append(item)
            items = new_items
        elif items is None:
            items = [i[0] for i in ShownPlaylists.get()]
            items += App().playlists.get_ids()
        FlowBoxView.populate(self, items)

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
        widget = PlaylistRoundedWidget(item[0], None, self._view_type)
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
        widget = FlowBoxView._add_items(self, playlist_ids,
                                        self.__obj,
                                        self._view_type)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

    def _on_map(self, widget):
        """
            Setup widget
        """
        FlowBoxView._on_map(self, widget)
        self.__signal_id = App().playlists.connect("playlists-changed",
                                                   self.__on_playlist_changed)
        if self.__obj is None:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", [Type.PLAYLISTS]))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", []))
            App().settings.set_value("state-three-ids",
                                     GLib.Variant("ai", []))
        else:
            App().window.emit("can-go-back-changed", True)
            App().window.emit("show-can-go-back", True)

    def _on_unmap(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        FlowBoxView._on_unmap(self, widget)
        if self.__signal_id is not None:
            App().playlists.disconnect(self.__signal_id)
            self.__signal_id = None

    def _on_item_activated(self, flowbox, widget):
        """
            Show Context view for activated album
            @param flowbox as Gtk.Flowbox
            @param widget as PlaylistRoundedWidget
        """
        if not self._view_type & ViewType.SMALL and\
                FlowBoxView._on_item_activated(self, flowbox, widget):
            return
        show_sidebar = App().settings.get_value("show-sidebar")
        sidebar_content = App().settings.get_enum("sidebar-content")
        show_genres = sidebar_content == SidebarContent.GENRES
        if not show_genres:
            App().window.emit("show-can-go-back", True)
            App().window.emit("can-go-back-changed", True)
        if show_sidebar and show_genres and not App().window.is_adaptive:
            App().window.container.list_two.select_ids([widget.data])
        else:
            App().window.container.show_view([Type.PLAYLISTS], [widget.data])

#######################
# PRIVATE             #
#######################
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

    def __on_playlist_changed(self, playlists, playlist_id):
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

    def __on_new_button_clicked(self, button):
        """
            Add a new playlist
            @param button as Gtk.Button
        """
        existing_playlists = []
        for (playlist_id, name, sortname) in App().playlists.get():
            existing_playlists.append(name)

        # Search for an available name
        count = 1
        name = _("New playlist ") + str(count)
        while name in existing_playlists:
            count += 1
            name = _("New playlist ") + str(count)
        App().playlists.add(name)
