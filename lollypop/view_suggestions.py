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

from gi.repository import Gtk, GLib, Pango

from gettext import gettext as _

from lollypop.view import View
from lollypop.utils import get_network_available
from lollypop.define import ViewType, StorageType, Size, MARGIN_SMALL
from lollypop.helper_filtering import FilteringHelper
from lollypop.view_albums_box import AlbumsPopularsBoxView
from lollypop.view_albums_box import AlbumsRandomGenreBoxView
from lollypop.view_artists_rounded import RoundedArtistsRandomView
from lollypop.widgets_banner_today import TodayBannerWidget


class SuggestionsView(View, FilteringHelper):
    """
        View showing suggestions to user
    """

    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        View.__init__(self, view_type)
        FilteringHelper.__init__(self)
        self.__grid = Gtk.Grid()
        self.__grid.get_style_context().add_class("padding")
        self.__grid.set_row_spacing(5)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.show()
        self._overlay = Gtk.Overlay.new()
        self._overlay.show()
        self._overlay.add(self._scrolled)
        self._viewport.add(self.__grid)
        album = TodayBannerWidget.get_today_album()
        if album.id is not None:
            self.__banner = TodayBannerWidget(album, self._view_type)
            self.__banner.show()
            self._overlay.add_overlay(self.__banner)
        else:
            self.__banner = None
        self.add(self._overlay)

    def populate(self):
        """
            Populate view
        """
        for _class in [AlbumsPopularsBoxView,
                       RoundedArtistsRandomView,
                       AlbumsRandomGenreBoxView]:
            view = _class(self._view_type)
            view.populate()
            self.__grid.add(view)
        if get_network_available("SPOTIFY") and\
                get_network_available("YOUTUBE"):
            from lollypop.view_albums_box import AlbumsSpotifyBoxView
            spotify_view = AlbumsSpotifyBoxView(_("You might like this"),
                                                self._view_type)
            spotify_view.populate(StorageType.SPOTIFY_SIMILARS)
            self.__grid.add(spotify_view)
            spotify_view = AlbumsSpotifyBoxView(_("New albums from Spotify"),
                                                self._view_type)
            spotify_view.populate(StorageType.SPOTIFY_NEW_RELEASES)
            self.__grid.add(spotify_view)
        GLib.timeout_add(250, self.__welcome_screen)

    def activate_child(self):
        """
            Activated typeahead row
        """
        for child in reversed(self.__grid.get_children()):
            child._box.unselect_all()
        for row in self.filtered:
            style_context = row.get_style_context()
            if style_context.has_class("typeahead"):
                row.activate()
            style_context.remove_class("typeahead")

    @property
    def filtered(self):
        """
            Get filtered widgets
            @return [Gtk.Widget]
        """
        children = []
        for child in reversed(self.__grid.get_children()):
            children += child.children
        return children

    @property
    def scroll_relative_to(self):
        """
            Relative to scrolled widget
            @return Gtk.Widget
        """
        return self

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
        return ({"view_type": self.view_type}, self.sidebar_id, position)

#######################
# PROTECTED           #
#######################
    def _on_adaptive_changed(self, window, status):
        """
            Update banner style
            @param window as Window
            @param status as bool
        """
        View._on_adaptive_changed(self, window, status)
        if self.__banner is not None:
            self.__banner.set_view_type(self._view_type)
            self.__set_margin()

    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        View._on_value_changed(self, adj)
        if self.__banner is not None:
            reveal = self.should_reveal_header(adj)
            self.__banner.set_reveal_child(reveal)
            if reveal:
                self.__set_margin()
            else:
                self._scrolled.get_vscrollbar().set_margin_top(0)

#######################
# PRIVATE             #
#######################
    def __set_margin(self):
        """
            Set margin from header
        """
        self.__grid.set_margin_top(self.__banner.height + MARGIN_SMALL)
        self._scrolled.get_vscrollbar().set_margin_top(self.__banner.height)

    def __welcome_screen(self):
        """
            Show welcome screen if view empty
        """
        # If any child visible, quit
        for child in self.__grid.get_children():
            if child.get_visible():
                return
            else:
                child.destroy()
        if self._view_type & ViewType.SCROLLED:
            self._scrolled.set_policy(Gtk.PolicyType.NEVER,
                                      Gtk.PolicyType.NEVER)
            self._viewport.set_property("valign", Gtk.Align.FILL)
        label = Gtk.Label.new(_("Welcome on Lollypop"))
        label.get_style_context().add_class("text-xx-large")
        label.set_property("valign", Gtk.Align.END)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_vexpand(True)
        label.show()
        label.get_style_context().add_class("opacity-transition")
        image = Gtk.Image.new_from_icon_name("org.gnome.Lollypop",
                                             Gtk.IconSize.INVALID)
        image.set_pixel_size(Size.SMALL)
        image.show()
        image.get_style_context().add_class("image-rotate-fast")
        image.get_style_context().add_class("opacity-transition")
        image.set_hexpand(True)
        image.set_vexpand(True)
        image.set_property("valign", Gtk.Align.START)
        self.__grid.add(label)
        self.__grid.add(image)
        GLib.idle_add(label.set_state_flags, Gtk.StateFlags.VISITED, True)
        GLib.idle_add(image.set_state_flags, Gtk.StateFlags.VISITED, True)
