# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from random import shuffle

from scarlatti.view_flowbox import FlowBoxView
from scarlatti.widgets_albums_genre import AlbumsGenreWidget
from scarlatti.define import App, Type, ViewType
from scarlatti.utils import get_icon_name
from scarlatti.objects_album import Album


class GenresBoxView(FlowBoxView):
    """
        Show genres in a FlowBox
    """

    def __init__(self, storage_type, view_type):
        """
            Init decade view
            @param storage_type as StorageType
            @param view_type as ViewType
        """
        from scarlatti.widgets_banner_flowbox import FlowboxBannerWidget
        FlowBoxView.__init__(self, storage_type,
                             view_type | ViewType.OVERLAY)
        self._empty_icon_name = get_icon_name(Type.GENRES)
        self.__banner = FlowboxBannerWidget([Type.GENRES], [], self.view_type)
        self.__banner.show()
        self.__banner.connect("play-all", self.__on_banner_play_all)
        self.add_widget(self._box, self.__banner)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            return App().genres.get_ids()

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"storage_type": self.storage_type,
                "view_type": self.view_type}

#######################
# PROTECTED           #
#######################
    def _get_child(self, value):
        """
            Get a child for view
            @param value as object
            @return child as AlbumsGenreWidget
        """
        if self.destroyed:
            return None
        widget = AlbumsGenreWidget(value, self.storage_type, self.view_type,
                                   self.font_height)
        self._box.insert(widget, -1)
        widget.show()
        return widget

    def _get_menu_widget(self, child):
        """
            Get menu widget
            @param child as AlbumSimpleWidget
            @return Gtk.Widget
        """
        from scarlatti.widgets_menu import MenuBuilder
        from scarlatti.menu_genre import GenreMenu
        menu = GenreMenu(child.data, self.view_type, App().window.folded)
        return MenuBuilder(menu)

    def _on_child_activated(self, flowbox, child):
        """
            Navigate into child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().window.container.show_view([Type.GENRES], child.data)

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
        album_ids = App().albums.get_ids([child.data], [],
                                         self.storage_type, False)
        albums = [Album(album_id) for album_id in album_ids]
        if albums:
            App().player.play_album_for_albums(albums[0], albums)

#######################
# PRIVATE             #
#######################
    def __on_banner_play_all(self, banner, random):
        """
            Play all albums
            @param banner as AlbumsBannerWidget
            @param random as bool
        """
        album_ids = App().genres.get_album_ids(True)
        if not album_ids:
            return
        albums = [Album(album_id) for album_id in album_ids]
        if random:
            shuffle(albums)
            App().player.play_album_for_albums(albums[0], albums)
        else:
            App().player.play_album_for_albums(albums[0], albums)
