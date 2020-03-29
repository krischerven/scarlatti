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

from gi.repository import Gio

from gettext import gettext as _
from random import shuffle

from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_album_simple import AlbumSimpleWidget
from lollypop.define import App, Type, ViewType, ScanUpdate, StorageType
from lollypop.objects_album import Album
from lollypop.utils import get_icon_name, get_network_available, popup_widget
from lollypop.utils import get_font_height, get_title_for_genres_artists
from lollypop.utils_file import get_youtube_dl
from lollypop.utils_album import get_album_ids_for
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.helper_signals import SignalsHelper, signals_map


class AlbumsBoxView(FlowBoxView, ViewController, SignalsHelper):
    """
        Show albums in a box
    """

    @signals_map
    def __init__(self, genre_ids, artist_ids, storage_type, view_type):
        """
            Init album view
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param storage_type as StorageType
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, storage_type, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
        self._storage_type = storage_type
        self.__populate_wanted = True
        if genre_ids and genre_ids[0] < 0:
            if genre_ids[0] == Type.WEB:
                (youtube_dl, env) = get_youtube_dl()
                if not Gio.NetworkMonitor.get_default(
                        ).get_network_available():
                    self._empty_message = _("Network not available")
                    self.show_placeholder(True)
                    self.__populate_wanted = False
                elif youtube_dl is None:
                    self._empty_message = _("Missing youtube-dl command")
                    self.show_placeholder(True)
                    self.__populate_wanted = False
                elif not get_network_available("YOUTUBE"):
                    self._empty_message =\
                        _("You need to enable YouTube in network settings")
                    self.show_placeholder(True)
                    self.__populate_wanted = False
            self._empty_icon_name = get_icon_name(genre_ids[0])
        return [
            (App().scanner, "album-updated", "_on_album_updated"),
            (App().player, "loading-changed", "_on_loading_changed")
        ]

    def populate(self, albums=[]):
        """
            Populate view for album ids
            Show artist_ids/genre_ids if empty
            @param albums as [Album]
        """
        def on_load(albums):
            if albums:
                FlowBoxView.populate(self, albums)
                self.show_placeholder(False)
            else:
                self.show_placeholder(True)

        def load():
            album_ids = get_album_ids_for(self._genre_ids, self._artist_ids,
                                          self.storage_type)
            albums = []
            for album_id in album_ids:
                album = Album(album_id, self._genre_ids, self._artist_ids)
                album.set_storage_type(self.storage_type)
                albums.append(album)
            return albums

        if albums:
            FlowBoxView.populate(self, albums)
        elif self.__populate_wanted:
            App().task_helper.run(load, callback=(on_load,))

    def insert_album(self, album, position):
        """
            Add a new album
            @param album as Album
            @param position as int
            @param cover_uri as int
        """
        widget = AlbumSimpleWidget(album, self._genre_ids,
                                   self._artist_ids, self.view_type,
                                   get_font_height())
        self._box.insert(widget, position)
        widget.show()
        widget.populate()

    def clear(self):
        """
            Clear view
        """
        for child in self._box.get_children():
            child.destroy()

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"genre_ids": self._genre_ids,
                "artist_ids": self._artist_ids,
                "storage_type": self._storage_type,
                "view_type": self.view_type & ~(ViewType.ADAPTIVE |
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
        widget = AlbumSimpleWidget(value,  self._genre_ids, self._artist_ids,
                                   self.view_type, self.font_height)
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
        from lollypop.menu_objects import AlbumMenu
        menu = AlbumMenu(child.data, self.storage_type,
                         self.view_type, App().window.is_adaptive)
        return MenuBuilder(menu)

    def _on_album_updated(self, scanner, album_id, scan_update):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param scan_update as ScanUpdate
        """
        if scan_update == ScanUpdate.ADDED:
            album_ids = get_album_ids_for(self._genre_ids, self._artist_ids,
                                          self.storage_type)
            if album_id in album_ids:
                index = album_ids.index(album_id)
                self.insert_album(Album(album_id), index)
        elif scan_update == ScanUpdate.MODIFIED:
            for child in self.children:
                if child.data.id == album_id:
                    child.data.reset_tracks()
                    break
        elif scan_update == ScanUpdate.REMOVED:
            for child in self.children:
                if child.data.id == album_id:
                    child.destroy()
                    break

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self._box.get_children():
            if child.data.id == album_id:
                child.set_artwork()

    def _on_loading_changed(self, player, status, track):
        """
            Update row loading status
            @param player as Player
            @param status as bool
            @param track as Track
        """
        for child in self.children:
            if child.data.id == track.album.id:
                context = child.artwork.get_style_context()
                if status:
                    context.add_class("load-animation")
                else:
                    context.remove_class("load-animation")
                break

    def _on_child_activated(self, flowbox, child):
        """
            Navigate into child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        if child.artwork is None:
            return

        def show_album(status, child):
            child.artwork.get_style_context().remove_class("load-animation")
            App().window.container.show_view([Type.ALBUM], child.data,
                                             self.storage_type)

        if child.data.storage_type & StorageType.COLLECTION:
            App().window.container.show_view([Type.ALBUM], child.data)
        else:
            child.artwork.get_style_context().add_class("load-animation")
            cancellable = Gio.Cancellable.new()
            App().task_helper.run(child.data.load_tracks,
                                  cancellable,
                                  callback=(show_album, child))

    def _on_tertiary_press_gesture(self, x, y, event):
        """
            Play albums
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        child = self._box.get_child_at_pos(x, y)
        if child is None or child.artwork is None:
            return

        def play_album(status, child):
            child.artwork.get_style_context().remove_class("load-animation")
            child.data.reset_tracks()
            App().player.play_album(child.data.get_with_skipping_allowed())

        if child.data.storage_type & StorageType.COLLECTION:
            App().player.play_album(child.data.get_with_skipping_allowed())
        else:
            child.artwork.get_style_context().add_class("load-animation")
            cancellable = Gio.Cancellable.new()
            App().task_helper.run(child.data.load_tracks,
                                  cancellable,
                                  callback=(play_album, child))


class AlbumsForGenresBoxView(AlbumsBoxView):
    """
        Show albums in a box for genres (static or not)
    """

    def __init__(self, genre_ids, artist_ids, storage_type, view_type):
        """
            Init album view
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param storage_type as StorageType
            @param view_type as ViewType
        """
        AlbumsBoxView.__init__(self, genre_ids, artist_ids, storage_type,
                               view_type | ViewType.OVERLAY)
        from lollypop.widgets_banner_flowbox import FlowboxBannerWidget
        self.__banner = FlowboxBannerWidget(genre_ids, artist_ids,
                                            view_type, True)
        self.__banner.show()
        self.__banner.connect("play-all", self.__on_banner_play_all)
        self.__banner.connect("show-menu", self.__on_banner_show_menu)
        self.add_widget(self._box, self.__banner)

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Set initial view state
            @param widget as GtK.Widget
        """
        AlbumsBoxView._on_map(self, widget)
        if self.view_type & ViewType.SCROLLED:
            self.scrolled.grab_focus()

#######################
# PRIVATE             #
#######################
    def __on_banner_play_all(self, banner, random):
        """
            Play all albums
            @param banner as AlbumsBannerWidget
            @param random as bool
        """
        albums = [c.data for c in self._box.get_children()]
        if not albums:
            return
        if random:
            shuffle(albums)
            App().player.play_album_for_albums(albums[0], albums)
        else:
            App().player.play_album_for_albums(albums[0], albums)

    def __on_banner_show_menu(self, banner, button):
        """
            Show contextual menu
            @param banner as AlbumsBannerWidget
            @param button as Gtk.Button
        """
        from lollypop.menu_objects import AlbumsMenu
        from lollypop.widgets_menu import MenuBuilder
        albums = []
        for child in self._box.get_children():
            if child.data.storage_type & StorageType.COLLECTION:
                albums.append(child.data)
        title = get_title_for_genres_artists(self._genre_ids, self._artist_ids)
        menu = AlbumsMenu(title, albums, App().window.is_adaptive)
        menu_widget = MenuBuilder(menu)
        menu_widget.show()
        popup_widget(menu_widget, button)


class AlbumsForYearsBoxView(AlbumsForGenresBoxView):
    """
        Years album box
    """

    def __init__(self, genre_ids, artist_ids, storage_type, view_type):
        """
            Init view
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param storage_type as StorageType
            @param view_type as ViewType
        """
        AlbumsForGenresBoxView.__init__(self, genre_ids, artist_ids,
                                        storage_type, view_type)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            items = []
            for year in self._artist_ids:
                items += App().albums.get_compilations_for_year(
                    year, self.storage_type)
                items += App().albums.get_albums_for_year(
                    year, self.storage_type)
            return [Album(album_id, [Type.YEARS], []) for album_id in items]

        App().task_helper.run(load, callback=(on_load,))


class AlbumsDeviceBoxView(AlbumsBoxView):
    """
        Device album box
    """

    def __init__(self, index, view_type):
        """
            Init view
            @param index as int
            @param view_type as ViewType
            @param index as int
        """
        AlbumsBoxView.__init__(self, [], [], StorageType.COLLECTION, view_type)
        self.add_widget(self._box)
        self.__index = index

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            album_ids = App().albums.get_synced_ids(0)
            album_ids += App().albums.get_synced_ids(self.__index)
            return [Album(album_id) for album_id in album_ids]

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        return None

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Set initial view state
            @param widget as GtK.Widget
        """
        AlbumsBoxView._on_map(self, widget)
        if self.view_type & ViewType.SCROLLED:
            self.scrolled.grab_focus()
