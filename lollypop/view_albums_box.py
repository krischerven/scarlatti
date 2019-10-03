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

from gi.repository import GLib, Gdk, Gtk, Gio, Pango

from gettext import gettext as _
from random import shuffle

from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_album_simple import AlbumSimpleWidget
from lollypop.define import App, Type, ViewType, MARGIN
from lollypop.objects_album import Album
from lollypop.utils import get_icon_name, get_network_available
from lollypop.utils import get_font_height, get_youtube_dl
from lollypop.helper_horizontal_scrolling import HorizontalScrollingHelper
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.widgets_banner_albums import AlbumsBannerWidget


class AlbumsBoxView(FlowBoxView, ViewController, SignalsHelper):
    """
        Show albums in a box
    """

    @signals_map
    def __init__(self, genre_ids, artist_ids, view_type=ViewType.DEFAULT):
        """
            Init album view
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self._widget_class = AlbumSimpleWidget
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
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
                elif not get_network_available("SPOTIFY") or\
                        not get_network_available("YOUTUBE"):
                    self._empty_message = _("You need to enable Spotify ") + \
                                          _("and YouTube in network settings")
                    self.show_placeholder(True)
                    self.__populate_wanted = False
            self._empty_icon_name = get_icon_name(genre_ids[0])
        return [
                (App().scanner, "album-updated", "_on_album_updated")
        ]

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            if items:
                FlowBoxView.populate(self, items)
                self.show_placeholder(False)
            else:
                self.show_placeholder(True)

        def load():
            album_ids = App().window.container.get_view_album_ids(
                self._genre_ids, self._artist_ids)
            return [Album(album_id, self._genre_ids, self._artist_ids)
                    for album_id in album_ids]

        if self.__populate_wanted:
            App().task_helper.run(load, callback=(on_load,))

    def insert_album(self, album, position):
        """
            Add a new album
            @param album as Album
            @param position as int
            @param cover_uri as int
        """
        widget = AlbumSimpleWidget(album, self._genre_ids,
                                   self._artist_ids, self._view_type,
                                   get_font_height())
        self._box.insert(widget, position)
        widget.show()
        widget.populate()

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"genre_ids": self._genre_ids,
                "artist_ids": self._artist_ids,
                "view_type": self.view_type}

#######################
# PROTECTED           #
#######################
    def _add_items(self, albums):
        """
            Add albums to the view
            Start lazy loading
            @param albums as [Album]
        """
        FlowBoxView._add_items(self, albums, self._genre_ids, self._artist_ids,
                               self._view_type)

    def _get_menu_widget(self, child):
        """
            Get menu widget
            @param child as AlbumSimpleWidget
            @return Gtk.Widget
        """
        from lollypop.widgets_menu import MenuBuilder
        from lollypop.menu_objects import AlbumMenu
        menu = AlbumMenu(child.data, self._view_type, App().window.is_adaptive)
        return MenuBuilder(menu)

    def _on_album_updated(self, scanner, album_id, added):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        if added and (not self._genre_ids or
                      self._genre_ids[0] >= 0 or
                      self._genre_ids[0] == Type.ALL):
            album_ids = App().window.container.get_view_album_ids(
                                            self._genre_ids,
                                            self._artist_ids)
            if album_id in album_ids:
                index = album_ids.index(album_id)
                self.insert_album(Album(album_id), index)
        else:
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

    def _on_primary_press_gesture(self, x, y, event):
        """
            Popup tracks menu at position
            @param x as int
            @param y as int
            @param event as Gdk.Event
        """
        child = self._box.get_child_at_pos(x, y)
        if child is None or child.artwork is None:
            return
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            from lollypop.pop_tracks import TracksPopover
            popover = TracksPopover(child.data)
            popover.set_relative_to(child.artwork)
            popover.set_position(Gtk.PositionType.BOTTOM)
            popover.popup()
        else:
            App().window.container.show_view([Type.ALBUM], child.data)

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
        App().player.play_album(child.data)


class AlbumsGenresBoxView(AlbumsBoxView):
    """
        Show albums in a box for genres (static or not)
    """

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init album view
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
        """
        AlbumsBoxView.__init__(self, genre_ids, artist_ids,
                               view_type |
                               ViewType.OVERLAY |
                               ViewType.SCROLLED)
        self.__banner = AlbumsBannerWidget(genre_ids, artist_ids, view_type)
        self.__banner.show()
        self.__banner.connect("play-all", self.__on_banner_play_all)
        self.__banner.connect("scroll", self._on_banner_scroll)
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
        albums = [c.data for c in self._box.get_children()]
        if not albums:
            return
        if random:
            shuffle(albums)
            App().player.play_album_for_albums(albums[0], albums)
        else:
            App().player.play_album_for_albums(albums[0], albums)


class AlbumsYearsBoxView(AlbumsGenresBoxView):
    """
        Years album box
    """

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init view
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
        """
        AlbumsGenresBoxView.__init__(self, genre_ids, artist_ids, view_type)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            items = []
            for year in self._artist_ids:
                items += App().albums.get_compilations_for_year(year)
                items += App().albums.get_albums_for_year(year)
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
        AlbumsBoxView.__init__(self, [], [], view_type)
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


class AlbumsLineView(AlbumsBoxView, HorizontalScrollingHelper):
    """
        Albums on a line
    """

    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        AlbumsBoxView.__init__(self, [Type.NONE], [], view_type)
        self.set_row_spacing(5)
        self.set_property("valign", Gtk.Align.START)
        self._label = Gtk.Label.new()
        self._label.set_ellipsize(Pango.EllipsizeMode.END)
        self._label.set_hexpand(True)
        self._label.set_property("halign", Gtk.Align.START)
        self._label.get_style_context().add_class("dim-label")
        self.__update_label(App().window.is_adaptive)
        self._backward_button = Gtk.Button.new_from_icon_name(
                                                        "go-previous-symbolic",
                                                        Gtk.IconSize.BUTTON)
        self._forward_button = Gtk.Button.new_from_icon_name(
                                                       "go-next-symbolic",
                                                       Gtk.IconSize.BUTTON)
        self._backward_button.get_style_context().add_class("menu-button-48")
        self._forward_button.get_style_context().add_class("menu-button-48")
        header = Gtk.Grid()
        header.set_column_spacing(10)
        header.add(self._label)
        header.add(self._backward_button)
        header.add(self._forward_button)
        header.set_margin_end(MARGIN)
        header.show_all()
        HorizontalScrollingHelper.__init__(self)
        self.add(header)
        self.add_widget(self._box)

    def populate(self, albums):
        """
            Configure widget based on albums
            @param items as [Album]
        """
        self._box.set_min_children_per_line(len(albums))
        FlowBoxView.populate(self, albums)
        if albums:
            self.show()

    @property
    def args(self):
        return None

#######################
# PROTECTED           #
#######################
    def _on_adaptive_changed(self, window, status):
        """
            Update label
            @param window as Window
            @param status as bool
        """
        AlbumsBoxView._on_adaptive_changed(self, window, status)
        self.__update_label(status)

    def _on_populated(self, widget, lazy_loading_id):
        """
            Update button state
            @param widget as Gtk.Widget
            @parma lazy_loading_id as int
        """
        AlbumsBoxView._on_populated(self, widget, lazy_loading_id)
        if self.is_populated:
            self._update_buttons()

#######################
# PRIVATE             #
#######################
    def __update_label(self, is_adaptive):
        """
            Update label style based on current adaptive state
            @param is_adaptive as bool
        """
        style_context = self._label.get_style_context()
        if is_adaptive:
            style_context.remove_class("text-x-large")
        else:
            style_context.add_class("text-x-large")


class AlbumsArtistBoxView(AlbumsLineView):
    """
        Artist album box
    """

    def __init__(self,  album, artist_id, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        AlbumsLineView.__init__(self, view_type)
        self.__album = album
        self.__artist_id = artist_id

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            AlbumsLineView.populate(self, items)

        def load():
            if self.__artist_id == Type.COMPILATIONS:
                album_ids = App().albums.get_compilation_ids(
                    self.__album.genre_ids)
            else:
                album_ids = App().albums.get_ids(
                    [self.__artist_id], [])
            if self.__album.id in album_ids:
                album_ids.remove(self.__album.id)
            return [Album(album_id) for album_id in album_ids]

        if self.__artist_id == Type.COMPILATIONS:
            self._label.set_text(_("Others compilations"))
        else:
            self._label.set_text(App().artists.get_name(self.__artist_id))
        App().task_helper.run(load, callback=(on_load,))


class AlbumsPopularsBoxView(AlbumsLineView):
    """
        Populars album box
    """

    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        AlbumsLineView.__init__(self, view_type)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            AlbumsLineView.populate(self, items)

        def load():
            album_ids = App().albums.get_populars_at_the_moment(20)
            return [Album(album_id) for album_id in album_ids]

        self._label.set_text(_("Popular albums at the moment"))
        App().task_helper.run(load, callback=(on_load,))


class AlbumsRandomGenreBoxView(AlbumsLineView):
    """
        Populars album box
    """

    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        AlbumsLineView.__init__(self, view_type)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            AlbumsLineView.populate(self, items)

        def load():
            (genre_id, genre) = App().genres.get_random()
            GLib.idle_add(self._label.set_text, genre)
            album_ids = App().albums.get_randoms(genre_id, 20)
            return [Album(album_id) for album_id in album_ids]

        App().task_helper.run(load, callback=(on_load,))


class AlbumsSpotifyBoxView(AlbumsLineView):
    """
        Spotify album box
    """

    @signals_map
    def __init__(self, text, view_type):
        """
            Init view
            @param text as str
            @param view_type as ViewType
        """
        AlbumsLineView.__init__(self, view_type)
        self._label.set_text(text)
        self.__cancellable = Gio.Cancellable()
        return [
                (App().settings, "changed::network-access",
                 "_on_network_access_changed"),
                (App().settings, "changed::network-access-acl",
                 "_on_network_access_changed")
        ]

    def populate(self, storage_type):
        """
            Populate view
            @param storage_type as StorageType
        """
        def on_load(items):
            AlbumsLineView.populate(self, items)

        def load():
            album_ids = App().albums.get_for_storage_type(storage_type, 20)
            return [Album(album_id) for album_id in album_ids]

        App().task_helper.run(load, callback=(on_load,))

#######################
# PROTECTED           #
#######################
    def _on_unmap(self, widget):
        """
            Cancel search
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()
        self.__cancellable = Gio.Cancellable()

    def _on_network_access_changed(self, *ignore):
        """
            Destroy if not allowed anymore
        """
        if not get_network_available("SPOTIFY") or\
                not get_network_available("YOUTUBE"):
            self.destroy()

#####################
# PRIVATE           #
#####################
