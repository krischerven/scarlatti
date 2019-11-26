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

from gi.repository import Gtk, Pango, Gio

from gettext import gettext as _
from random import shuffle

from lollypop.view_flowbox import FlowBoxView
from lollypop.define import App, Type, MARGIN, ViewType, OrderBy
from lollypop.helper_horizontal_scrolling import HorizontalScrollingHelper
from lollypop.widgets_artist_rounded import RoundedArtistWidget
from lollypop.objects_album import Album
from lollypop.utils import get_icon_name, get_font_height
from lollypop.helper_signals import SignalsHelper, signals_map


class RoundedArtistsView(FlowBoxView, SignalsHelper):
    """
        Show artists in a FlowBox
    """

    @signals_map
    def __init__(self, view_type):
        """
            Init artist view
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type)
        self.connect("destroy", self.__on_destroy)
        self._empty_icon_name = get_icon_name(Type.ARTISTS)
        return [
            (App().art, "artist-artwork-changed",
             "_on_artist_artwork_changed"),
            (App().scanner, "artist-updated", "_on_artist_updated")
        ]

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            if App().settings.get_value("show-performers"):
                ids = App().artists.get_performers()
            else:
                ids = App().artists.get()
            return ids

        App().task_helper.run(load, callback=(on_load,))

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
        widget = RoundedArtistWidget(value, self._view_type, self.font_height)
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
        menu = ArtistMenu(child.data, self._view_type,
                          App().window.is_adaptive)
        section = Gio.Menu()
        menu.append_section(_("Similar artists"), section)
        menu_widget = MenuBuilder(menu, True)
        scrolled = menu_widget.get_child_by_name("main")
        menu_widget.show()
        menu_ext = SimilarsMenu()
        menu_ext.show()
        menu_ext.populate(child.data)
        # scrolled -> viewport -> box
        scrolled.get_child().get_child().add(menu_ext)
        scrolled.set_size_request(300, 400)
        return menu_widget

    def _on_child_activated(self, flowbox, child):
        """
            Navigate into child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().window.container.show_view([Type.ARTISTS], [child.data])

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
        album_ids = App().albums.get_ids([child.data], [])
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
            artist_ids = App().artists.get_ids()
            # Can happen during scan
            if artist_id not in artist_ids:
                return
            position = artist_ids.index(artist_id)
            artist_name = App().artists.get_name(artist_id)
            sortname = App().artists.get_sortname(artist_id)
            widget = RoundedArtistWidget((artist_id, artist_name, sortname),
                                         self._view_type,
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

    def __init__(self):
        """
            Init artist view
        """
        from lollypop.widgets_banner_albums import AlbumsBannerWidget
        RoundedArtistsView.__init__(self, ViewType.SCROLLED | ViewType.OVERLAY)
        self.__banner = AlbumsBannerWidget([Type.ARTISTS], [], self._view_type)
        self.__banner.show()
        self.__banner.connect("play-all", self.__on_banner_play_all)
        self.add_widget(self._box, self.__banner)

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {}

#######################
# PRIVATE             #
#######################
    def __on_banner_play_all(self, banner, random):
        """
            Play all albums
            @param banner as AlbumsBannerWidget
            @param random as bool
        """
        album_ids = App().albums.get_ids([], [], True, OrderBy.ARTIST)
        if not album_ids:
            return
        albums = [Album(album_id) for album_id in album_ids]
        if random:
            shuffle(albums)
            App().player.play_album_for_albums(albums[0], albums)
        else:
            App().player.play_album_for_albums(albums[0], albums)


class RoundedArtistsRandomView(RoundedArtistsView, HorizontalScrollingHelper):
    """
        Show 6 random artists in a FlowBox
    """

    def __init__(self, view_type):
        """
            Init artist view
            @param view_type as ViewType
        """
        RoundedArtistsView.__init__(self, view_type)
        self.set_row_spacing(5)
        self._label = Gtk.Label.new()
        self._label.set_ellipsize(Pango.EllipsizeMode.END)
        self._label.get_style_context().add_class("dim-label")
        self.__update_label(App().window.is_adaptive)
        self._label.set_hexpand(True)
        self._label.set_property("halign", Gtk.Align.START)
        self._backward_button = Gtk.Button.new_from_icon_name(
                                                    "go-previous-symbolic",
                                                    Gtk.IconSize.BUTTON)
        self._forward_button = Gtk.Button.new_from_icon_name(
                                                   "go-next-symbolic",
                                                   Gtk.IconSize.BUTTON)
        self._backward_button.get_style_context().add_class("menu-button")
        self._forward_button.get_style_context().add_class("menu-button")
        header = Gtk.Grid()
        header.set_column_spacing(10)
        header.add(self._label)
        header.add(self._backward_button)
        header.add(self._forward_button)
        header.set_margin_end(MARGIN)
        header.show_all()
        HorizontalScrollingHelper.__init__(self)
        self.add(header)
        self._label.set_property("halign", Gtk.Align.START)
        self._box.set_property("halign", Gtk.Align.CENTER)
        self.add_widget(self._box)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            self._box.set_min_children_per_line(len(items))
            FlowBoxView.populate(self, items)
            if items:
                self.show()

        def load():
            ids = App().artists.get_randoms(15)
            return ids

        self._label.set_text(_("Why not listen to?"))
        App().task_helper.run(load, callback=(on_load,))

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
        RoundedArtistsView._on_adaptive_changed(self, window, status)
        self.__update_label(status)

    def _on_populated(self, widget):
        """
            Update button state
            @param widget as Gtk.Widget
        """
        RoundedArtistsView._on_populated(self, widget)
        if self.is_populated:
            self._update_buttons()

    def _on_artist_updated(self, scanner, artist_id, add):
        pass

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
