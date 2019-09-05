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

from random import shuffle

from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_albums_decade import AlbumsDecadeWidget
from lollypop.define import App, Type, ViewType, OrderBy
from lollypop.utils import get_icon_name, popup_widget
from lollypop.objects_album import Album


class DecadesBoxView(FlowBoxView):
    """
        Show decades in a FlowBox
    """

    def __init__(self):
        """
            Init decade view
        """
        from lollypop.widgets_banner_albums import AlbumsBannerWidget
        FlowBoxView.__init__(self, ViewType.SCROLLED | ViewType.OVERLAY)
        self._widget_class = AlbumsDecadeWidget
        self._empty_icon_name = get_icon_name(Type.YEARS)
        self.__banner = AlbumsBannerWidget([Type.YEARS], [], self._view_type)
        self.__banner.show()
        self.__banner.connect("play-all", self.__on_banner_play_all)
        self.__banner.connect("scroll", self._on_banner_scroll)
        self.add_widget(self._box, self.__banner)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            (years, unknown) = App().albums.get_years()
            decades = []
            decade = []
            current_d = None
            for year in sorted(years):
                d = year // 10
                if current_d is not None and current_d != d:
                    current_d = d
                    decades.append(decade)
                    decade = []
                current_d = d
                decade.append(year)
            if decade:
                decades.append(decade)
            return decades

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        return ({"view_type": self.view_type}, self.sidebar_id, self.position)

#######################
# PROTECTED           #
#######################
    def _add_items(self, item_ids, *args):
        """
            Add albums to the view
            Start lazy loading
            @param item ids as [int]
        """
        FlowBoxView._add_items(self, item_ids, self._view_type)

    def _on_child_activated(self, flowbox, child):
        """
            Enter child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().window.container.show_view([Type.YEARS], child.data)

    def _on_secondary_press_gesture(self, x, y, event):
        """
            Popup menu for artist at position
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        self._on_primary_long_press_gesture(x, y)

    def _on_primary_long_press_gesture(self, x, y):
        """
            Popup menu for artist at position
            @param x as int
            @param y as int
        """
        child = self._box.get_child_at_pos(x, y)
        if child is None or child.artwork is None:
            return
        self.__popup_menu(child)

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, child):
        """
            Popup album menu at position
            @param child ad PlaylistRoundedWidget
        """
        from lollypop.menu_decade import DecadeMenu
        from lollypop.widgets_menu import MenuBuilder
        menu = DecadeMenu(child.data, self._view_type,
                          App().window.is_adaptive)
        menu_widget = MenuBuilder(menu)
        menu_widget.show()
        popup_widget(menu_widget, child.artwork)

    def __on_banner_play_all(self, banner, random):
        """
            Play all albums
            @param banner as AlbumsBannerWidget
            @param random as bool
        """
        album_ids = App().albums.get_ids([], [], True, OrderBy.YEAR_ASC)
        if not album_ids:
            return
        albums = [Album(album_id) for album_id in album_ids]
        if random:
            shuffle(albums)
            App().player.play_album_for_albums(albums[0], albums)
        else:
            App().player.play_album_for_albums(albums[0], albums)
