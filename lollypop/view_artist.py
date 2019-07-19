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

from gi.repository import Gtk

from lollypop.define import App, ViewType, MARGIN
from lollypop.view import View
from lollypop.view_albums_box import AlbumsBoxView
from lollypop.widgets_banner_artist import ArtistBannerWidget


class ArtistView(View):
    """
        Show artist albums
    """

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init ArtistView
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
        """
        View.__init__(self, view_type)
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
        self.__banner = ArtistBannerWidget(genre_ids, artist_ids)
        self.__banner.init_background()
        self.__banner.show()
        self.__overlay = Gtk.Overlay()
        self.__overlay.show()
        self.__overlay.add_overlay(self.__banner)
        self.__album_box = AlbumsBoxView(genre_ids,
                                         artist_ids,
                                         (view_type |
                                          ViewType.ALBUM) &
                                         ~ViewType.SCROLLED)
        self.__album_box.set_margin_top(self.__banner.height)
        self.__album_box.get_style_context().add_class("padding")
        self.__album_box.show()
        if self._view_type & ViewType.SCROLLED:
            self.__overlay.add(self._scrolled)
            self._viewport.add(self.__album_box)
            self._scrolled.get_vscrollbar().set_margin_top(
                self.__banner.height)
        else:
            self.__overlay.add(self.__album_box)
        self.add(self.__overlay)
        if len(self._artist_ids) > 1:
            self.__banner.collapse(True)

    def populate(self):
        """
            Populate view
            @param albums as [album]
        """
        self.__album_box.populate()

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

    @property
    def indicator(self):
        return self.__album_box.indicator

    @property
    def filtered(self):
        return self.__album_box.filtered

    @property
    def scroll_shift(self):
        """
            Add scroll shift on y axes
            @return int
        """
        return self.__banner.height + MARGIN

#######################
# PROTECTED           #
#######################
    def _on_value_changed(self, adj):
        """
            Update scroll value and check for lazy queue
            @param adj as Gtk.Adjustment
        """
        if adj.get_value() == adj.get_lower():
            self.__banner.collapse(False)
            self.__album_box.set_margin_top(
                self.__banner.height)
        else:
            self.__album_box.set_margin_top(self.__banner.height)
            self.__banner.collapse(True)
        if self._view_type & ViewType.SCROLLED:
            self._scrolled.get_vscrollbar().set_margin_top(
                self.__banner.height)

    def _on_adaptive_changed(self, window, status):
        """
            Update banner style
            @param window as Window
            @param status as bool
        """
        View._on_adaptive_changed(self, window, status)
        self.__banner.set_view_type(self._view_type)
        self.__album_box.set_margin_top(self.__banner.height)

#######################
# PRIVATE             #
#######################
    def __update_jump_button(self):
        """
            Update jump button status
        """
        found = False
        for child in self.children:
            if child.album.id == App().player.current_track.album.id:
                found = True
                break
        if found:
            self._jump_button.set_sensitive(True)
        else:
            self._jump_button.set_sensitive(False)
