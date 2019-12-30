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
from lollypop.define import ViewType, StorageType, Size
from lollypop.helper_filtering import FilteringHelper
from lollypop.view_albums_line import AlbumsPopularsLineView
from lollypop.view_albums_line import AlbumsRandomGenresLineView
from lollypop.view_artists_rounded_line import RoundedArtistsLineView
from lollypop.widgets_banner_today import TodayBannerWidget


class SuggestionsView(FilteringHelper, View):
    """
        View showing suggestions to user
    """

    def __init__(self, view_type=ViewType.DEFAULT):
        """
            Init view
            @param view_type as ViewType
        """
        View.__init__(self, view_type | ViewType.SCROLLED | ViewType.OVERLAY)
        FilteringHelper.__init__(self)
        self.__grid = Gtk.Grid()
        self.__grid.get_style_context().add_class("padding")
        self.__grid.set_row_spacing(5)
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.show()
        album = TodayBannerWidget.get_today_album()
        if album is not None:
            self.__banner = TodayBannerWidget(album, self._view_type)
            self.__banner.show()
        else:
            self.__banner = None
        self.add_widget(self.__grid, self.__banner)

    def populate(self):
        """
            Populate view
        """
        for _class in [AlbumsPopularsLineView,
                       RoundedArtistsLineView,
                       AlbumsRandomGenresLineView]:
            view = _class(self._view_type)
            view.populate()
            self.__grid.add(view)
        if get_network_available("SPOTIFY") and\
                get_network_available("YOUTUBE"):
            from lollypop.view_albums_line import AlbumsSpotifyLineView
            spotify_view = AlbumsSpotifyLineView(_("You might like this"),
                                                 self._view_type)
            spotify_view.populate(StorageType.SPOTIFY_SIMILARS)
            self.__grid.add(spotify_view)
            spotify_view = AlbumsSpotifyLineView(_("New albums from Spotify"),
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
            Get default args for __class__
            @return {}
        """
        return {"view_type": self.view_type}

#######################
# PRIVATE             #
#######################
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
        label = Gtk.Label.new(_("Welcome to Lollypop"))
        label.get_style_context().add_class("text-xx-large")
        label.set_property("valign", Gtk.Align.END)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_vexpand(True)
        label.show()
        label.get_style_context().add_class("opacity-transition")
        image = Gtk.Image.new_from_icon_name("org.gnome.Lollypop",
                                             Gtk.IconSize.INVALID)
        image.set_pixel_size(Size.MINI)
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
