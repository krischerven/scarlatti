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

from random import shuffle

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type, ViewType, OrderBy
from lollypop.widgets_artist_rounded import RoundedArtistWidget
from lollypop.objects_album import Album
from lollypop.utils import get_icon_name, get_font_height
from lollypop.utils import get_default_storage_type
from lollypop.helper_signals import SignalsHelper, signals_map


class RoundedArtistsView(FlowBoxView, SignalsHelper):
    """
        Show artists in a FlowBox
    """

    @signals_map
    def __init__(self, storage_type, view_type):
        """
            Init artist view
            @param storage_type as StorageType
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, storage_type, view_type)
        self.connect("destroy", self.__on_destroy)
        self._empty_icon_name = get_icon_name(Type.ARTISTS)
        return [
            (App().art, "artist-artwork-changed",
             "_on_artist_artwork_changed"),
            (App().scanner, "artist-updated", "_on_artist_updated")
        ]

    def populate(self, artist_ids=[]):
        """
            Populate view with artist id
            Show all artists if empty
            @param artist_ids as [int]
        """
        def on_load(artist_ids):
            FlowBoxView.populate(self, artist_ids)

        def load():
            if App().settings.get_value("show-performers"):
                ids = App().artists.get_performers([], self.storage_type)
            else:
                ids = App().artists.get([], self.storage_type)
            return ids

        if artist_ids:
            FlowBoxView.populate(self, artist_ids)
        else:
            App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"view_type": self.view_type,
                "storage_type": self.storage_type}

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
        widget = RoundedArtistWidget(value, self.view_type, self.font_height)
        self._box.insert(widget, -1)
        widget.show()
        return widget

    def _get_menu_widget(self, child):
        """
            Get menu widget
            @param child as AlbumSimpleWidget
            @return Gtk.Widget
        """
        from lollypop.widgets_menu import MenuBuilder
        from lollypop.menu_artist import ArtistMenu
        from lollypop.menu_similars import SimilarsMenu
        menu = ArtistMenu(child.data, self.storage_type, self.view_type,
                          App().window.is_adaptive)
        menu_widget = MenuBuilder(menu, False)
        menu_widget.show()
        menu_ext = SimilarsMenu()
        menu_ext.show()
        menu_ext.populate(child.data)
        menu_widget.append_widget(menu_ext)
        return menu_widget

    def _on_child_activated(self, flowbox, child):
        """
            Navigate into child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().window.container.show_view([Type.ARTISTS], [child.data],
                                         self.storage_type)

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
        album_ids = App().albums.get_ids([child.data], [], self.storage_type)
        albums = [Album(album_id) for album_id in album_ids]
        if albums:
            App().player.play_album_for_albums(albums[0], albums)

    def _on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        for child in self._box.get_children():
            if child.name == prefix:
                child.set_artwork()

    def _on_artist_updated(self, scanner, artist_id, add):
        """
            Add/remove artist to/from list
            @param scanner as CollectionScanner
            @param artist_id as int
            @param add as bool
        """
        if add:
            storage_type = get_default_storage_type()
            artist_ids = App().artists.get_ids([], storage_type)
            # Can happen during scan
            if artist_id not in artist_ids:
                return
            position = artist_ids.index(artist_id)
            artist_name = App().artists.get_name(artist_id)
            sortname = App().artists.get_sortname(artist_id)
            widget = RoundedArtistWidget((artist_id, artist_name, sortname),
                                         self.view_type,
                                         get_font_height())
            self._box.insert(widget, position)
            widget.show()
            widget.populate()
        else:
            for child in self._box.get_children():
                if child.data == artist_id:
                    child.destroy()
                    break

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Stop loading
            @param widget as Gtk.Widget
        """
        RoundedArtistsView.stop(self)


class RoundedArtistsViewWithBanner(RoundedArtistsView):
    """
        Show rounded artist view with a banner
    """

    def __init__(self, storage_type, view_type):
        """
            Init artist view
            @param storage_type as StorageType
            @param view_type as ViewType
        """
        from lollypop.widgets_banner_flowbox import FlowboxBannerWidget
        RoundedArtistsView.__init__(self, storage_type,
                                    view_type | ViewType.OVERLAY)
        self.__banner = FlowboxBannerWidget([Type.ARTISTS], [], self.view_type)
        self.__banner.show()
        self.__banner.connect("play-all", self.__on_banner_play_all)
        self.add_widget(self._box, self.__banner)

#######################
# PRIVATE             #
#######################
    def __on_banner_play_all(self, banner, random):
        """
            Play all albums
            @param banner as AlbumsBannerWidget
            @param random as bool
        """
        album_ids = App().albums.get_ids([], [], self.storage_type,
                                         True, OrderBy.ARTIST)
        if not album_ids:
            return
        albums = [Album(album_id) for album_id in album_ids]
        if random:
            shuffle(albums)
            App().player.play_album_for_albums(albums[0], albums)
        else:
            App().player.play_album_for_albums(albums[0], albums)
