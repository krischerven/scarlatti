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

from gi.repository import Gtk, GLib


from lollypop.define import App, ViewType
from lollypop.view import View
from lollypop.view_albums_box import AlbumsBoxView
from lollypop.view_artist_common import ArtistViewCommon


class ArtistViewSmall(View, ArtistViewCommon):
    """
        Show artist albums and tracks
    """

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init ArtistView
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
        """
        View.__init__(self)
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
        self._albums = []
        ArtistViewCommon.__init__(self)
        self._jump_button.hide()
        self.__overlay = Gtk.Overlay()
        self.__overlay.show()
        self.__overlay.add_overlay(self._banner)
        self.__album_box = AlbumsBoxView(genre_ids,
                                         artist_ids,
                                         view_type)
        self._banner.collapse(True)
        self.__album_box.set_margin_top(self._banner.height)
        self.__album_box.show()
        self.__overlay.add_overlay(self.__album_box)
        self.add(self.__overlay)

    def populate(self, albums):
        """
            Populate view
            @param albums as [album]
        """
        self._albums = albums
        self.__album_box.populate(list(albums))

    def search_for_child(self, text):
        return self.__album_box.search_for_child(text)

    def activate_child(self):
        self.__album_box.activate_child()

    def search_prev(self, text):
        self.__album_box.search_prev(text)

    def search_next(self, text):
        self.__album_box.search_next(text)

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, {}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        return ({"genre_ids": self._genre_ids,
                 "artist_ids": self._artist_ids}, {"albums": self._albums},
                self._sidebar_id, position)

    @property
    def indicator(self):
        return self.__album_box.indicator

    @property
    def filtered(self):
        return self.__album_box.filtered

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Connect signals and set active ids
            @param widget as Gtk.Widget
        """
        View._on_map(self, widget)
        App().settings.set_value("state-one-ids",
                                 GLib.Variant("ai", self._genre_ids))
        App().settings.set_value("state-two-ids",
                                 GLib.Variant("ai", self._artist_ids))
        App().settings.set_value("state-three-ids",
                                 GLib.Variant("ai", []))

    def _on_adaptive_changed(self, window, status):
        """
            Update banner style
            @param window as Window
            @param status as bool
        """
        if not status:
            App().window.container.show_view(
                self._genre_ids, self._artist_ids, True)
            # Destroy after any animation
            GLib.idle_add(self.destroy, priority=GLib.PRIORITY_LOW)

#######################
# PRIVATE             #
#######################
