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

from gi.repository import GLib, Gtk, Gio

from gettext import gettext as _

from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_album_simple import AlbumSimpleWidget
from lollypop.define import App, Type, ViewType
from lollypop.objects_album import Album
from lollypop.utils import get_icon_name, get_network_available
from lollypop.utils import get_font_height
from lollypop.controller_view import ViewController, ViewControllerType


class AlbumsBoxView(FlowBoxView, ViewController):
    """
        Show albums in a box
    """

    def __init__(self, genre_ids, artist_ids, view_type=ViewType.SCROLLED):
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
        if genre_ids and genre_ids[0] < 0:
            if genre_ids[0] == Type.WEB:
                if not Gio.NetworkMonitor.get_default(
                        ).get_network_available():
                    self._empty_message = _("Network not available")
                    self._box.hide()
                elif GLib.find_program_in_path("youtube-dl") is None:
                    self._empty_message = _("Missing youtube-dl command")
                    self._box.hide()
                elif not get_network_available("SPOTIFY") or\
                        not get_network_available("YOUTUBE"):
                    self._empty_message = _("You need to enable Spotify ") + \
                                          _("and YouTube in network settings")
                    self._box.hide()
            self._empty_icon_name = get_icon_name(genre_ids[0])
        if view_type & ViewType.SMALL and view_type & ViewType.SCROLLED:
            self._scrolled.set_policy(Gtk.PolicyType.NEVER,
                                      Gtk.PolicyType.NEVER)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            album_ids = App().window.container.get_view_album_ids(
                self._genre_ids, self._artist_ids)
            return [Album(album_id, self._genre_ids, self._artist_ids)
                    for album_id in album_ids]

        App().task_helper.run(load, callback=(on_load,))

    def insert_album(self, album, position):
        """
            Add a new album
            @param album as Album
            @param position as int
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
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        view_type = self._view_type & ~self.view_sizing_mask
        return ({"genre_ids": self._genre_ids,
                 "artist_ids": self._artist_ids,
                 "view_type": view_type},
                self._sidebar_id, position)

#######################
# PROTECTED           #
#######################
    def _add_items(self, albums):
        """
            Add albums to the view
            Start lazy loading
            @param albums as [Album]
        """
        widget = FlowBoxView._add_items(self, albums,
                                        self._genre_ids,
                                        self._artist_ids,
                                        self._view_type)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

    def _on_map(self, widget):
        """
            Restore list position if needed
            @param widget as Gtk.Widget
        """
        def on_populated(selection_list, ids):
            selection_list.disconnect_by_func(on_populated)
            selection_list.select_ids(ids, False)

        FlowBoxView._on_map(self, widget)
        # Restore list view if needed
        if self._sidebar_id == Type.GENRES_LIST and\
                not self._view_type & ViewType.ALBUM:
            genre_ids = []
            for album in self._items:
                for genre_id in album.genre_ids:
                    if genre_id not in genre_ids:
                        genre_ids.append(genre_id)
            selection_list = App().window.container.list_view
            selection_list.connect("populated", on_populated, genre_ids)

    def _on_album_updated(self, scanner, album_id, added):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        album_ids = App().window.container.get_view_album_ids(
                                            self._genre_ids,
                                            self._artist_ids)
        if album_id not in album_ids:
            return
        index = album_ids.index(album_id)
        self.insert_album(Album(album_id), index)

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self._box.get_children():
            if child.album.id == album_id:
                child.set_artwork()

    def _on_item_activated(self, flowbox, album_widget):
        """
            Show Context view for activated album
            @param flowbox as Gtk.Flowbox
            @param album_widget as AlbumSimpleWidget
        """
        if not self._view_type & ViewType.SMALL and\
                FlowBoxView._on_item_activated(self, flowbox, album_widget):
            return
        if album_widget.artwork is None:
            return
        if self._genre_ids and self._genre_ids[0] == Type.YEARS:
            album = Album(album_widget.album.id)
        else:
            album = Album(album_widget.album.id,
                          self._genre_ids, self._artist_ids)
        App().window.container.show_view([Type.ALBUM], album)

#######################
# PRIVATE             #
#######################
    def __on_album_popover_closed(self, popover, album_widget):
        """
            Remove overlay and restore opacity
            @param popover as Popover
            @param album_widget as AlbumWidget
        """
        album_widget.lock_overlay(False)
        album_widget.artwork.set_opacity(1)


class AlbumsYearsBoxView(AlbumsBoxView):
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
        AlbumsBoxView.__init__(self, genre_ids, artist_ids, view_type)

    def do_populate(self):
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


class OthersAlbumsBoxView(AlbumsBoxView):
    """
        Others album box
    """

    def __init__(self, album, artist_id, view_type):
        """
            Init view
            @param album as Album
            @param artist_id as int
            @param view_type as ViewType
            @param index as int
        """
        AlbumsBoxView.__init__(self, [], [artist_id], view_type)
        self.__album = album
        self.__artist_id = artist_id

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            if items:
                artist = GLib.markup_escape_text(
                    App().artists.get_name(self.__artist_id))
                label = Gtk.Label.new()
                label.set_markup(
                                 '''<span size="large" alpha="40000"
                                     weight="bold">%s %s</span>''' %
                                 (_("Others albums from"), artist))
                label.set_property("halign", Gtk.Align.START)
                label.set_margin_top(40)
                label.show()
                self.insert_row(0)
                self.attach(label, 0, 0, 1, 1)
                FlowBoxView.populate(self, items)
                self.show()

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


class AlbumsPopularsBoxView(AlbumsBoxView):
    """
        Populars album box
    """

    def __init__(self):
        """
            Init view
        """
        AlbumsBoxView.__init__(self, [], [], ViewType.DEFAULT)
        self.insert_row(0)
        self.set_row_spacing(10)
        label = Gtk.Label.new(_("Popular albums at the moment:"))
        style_context = label.get_style_context()
        style_context.add_class("text-x-large")
        style_context.add_class("dim-label")
        label.show()
        self.attach(label, 0, 0, 1, 1)
        self.get_style_context().add_class("padding")
        label.set_property("halign", Gtk.Align.START)
        self._box.set_property("halign", Gtk.Align.CENTER)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            album_ids = App().albums.get_populars_at_the_moment(6)
            return [Album(album_id) for album_id in album_ids]

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        return None


class AlbumsRandomGenreBoxView(AlbumsBoxView):
    """
        Populars album box
    """

    def __init__(self):
        """
            Init view
        """
        AlbumsBoxView.__init__(self, [], [], ViewType.DEFAULT)
        self.insert_row(0)
        self.set_row_spacing(10)
        (self.__genre_id, genre) = App().genres.get_random()
        label = Gtk.Label.new(_("Let's play some %s:") % genre)
        style_context = label.get_style_context()
        style_context.add_class("text-x-large")
        style_context.add_class("dim-label")
        label.show()
        self.attach(label, 0, 0, 1, 1)
        self.get_style_context().add_class("padding")
        label.set_property("halign", Gtk.Align.START)
        self._box.set_property("halign", Gtk.Align.CENTER)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            album_ids = App().albums.get_randoms(self.__genre_id, 6)
            return [Album(album_id) for album_id in album_ids]

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        return None
