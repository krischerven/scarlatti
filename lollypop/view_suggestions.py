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
from lollypop.view_albums_box import AlbumsPopularsBoxView
from lollypop.view_albums_box import AlbumsRandomGenreBoxView
from lollypop.view_artists_rounded import RoundedArtistsRandomView


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
        if view_type & ViewType.SCROLLED:
            self._viewport.add(self.__grid)
            self._viewport.set_property("valign", Gtk.Align.START)
            self._scrolled.set_property("expand", True)
            self.add(self._scrolled)
        else:
            self.add(self.__grid)

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
    def view_sizing_mask(self):
        """
            Get mask for adaptive mode
            @return ViewType
        """
        return ViewType.MEDIUM

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
        return ({"view_type": view_type}, self._sidebar_id, position)

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        pass

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
