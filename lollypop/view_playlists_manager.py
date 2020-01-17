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

from locale import strcoll

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type, ViewType
from lollypop.utils import popup_widget, tracks_to_albums
from lollypop.objects_track import Track
from lollypop.widgets_playlist_rounded import PlaylistRoundedWidget
from lollypop.widgets_banner_playlists import PlaylistsBannerWidget
from lollypop.shown import ShownPlaylists
from lollypop.helper_signals import SignalsHelper, signals_map


class PlaylistsManagerView(FlowBoxView, SignalsHelper):
    """
        Show playlists in a FlowBox
    """

    @signals_map
    def __init__(self, view_type):
        """
            Init decade view
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type |
                             ViewType.SCROLLED | ViewType.OVERLAY)
        self.__signal_id = None
        self._empty_icon_name = "emblem-documents-symbolic"
        if self.args is None:
            self.add_widget(self._box, None)
        else:
            self.__banner = PlaylistsBannerWidget(self)
            self.__banner.show()
            self.add_widget(self._box, self.__banner)
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

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"view_type": self.view_type}

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
        # Compatibility with SelectionList
        if isinstance(value, tuple):
            value = value[0]
        widget = PlaylistRoundedWidget(value, self._view_type,
                                       self.font_height)
        self._box.insert(widget, -1)
        widget.show()
        return widget

    def _on_child_activated(self, flowbox, child):
        """
            Navigate into child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().window.container.show_view([Type.PLAYLISTS], child.data)

    def _on_tertiary_press_gesture(self, x, y, event):
        """
            Play artist
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        child = self._box.get_child_at_pos(x, y)
        if child is None or child.artwork is None:
            return
        track_ids = []
        if child.data > 0 and App().playlists.get_smart(child.data):
            request = App().playlists.get_smart_sql(child.data)
            if request is not None:
                track_ids = App().db.execute(request)
        else:
            track_ids = App().playlists.get_track_ids(child.data)
        tracks = [Track(track_id) for track_id in track_ids]
        albums = tracks_to_albums(tracks)
        if albums:
            App().player.play_album_for_albums(albums[0], albums)

    def _on_secondary_press_gesture(self, x, y, event):
        """
            Show Context view for activated album
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        self._on_primary_long_press_gesture(x, y)

    def _on_primary_long_press_gesture(self, x, y):
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
                self.add_value(playlist_id)
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
            Popup menu for playlist
            @param child as PlaylistRoundedWidget
        """
        from lollypop.widgets_menu import MenuBuilder
        from lollypop.menu_playlist import PlaylistMenu, PlaylistMenuExt
        menu = PlaylistMenu(child.data, App().window.is_adaptive)
        menu_widget = MenuBuilder(menu)
        if child.data >= 0:
            menu_widget = MenuBuilder(menu)
            menu_ext = PlaylistMenuExt(child.data)
            menu_ext.show()
            menu_widget.append_widget(menu_ext)
        else:
            menu_widget = MenuBuilder(menu)
        menu_widget.show()
        popup_widget(menu_widget, child)

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
