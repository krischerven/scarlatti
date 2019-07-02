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
from lollypop.objects import Album
from lollypop.view import View
from lollypop.view_albums_box import AlbumsBoxView
from lollypop.view_artist_common import ArtistViewCommon


class ArtistViewSmall(View, ArtistViewCommon):
    """
        Show artist albums and tracks
    """

    def __init__(self, artist_ids, genre_ids):
        """
            Init ArtistView
            @param artist_id as int (Current if None)
            @param genre_id as int
        """
        View.__init__(self)
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
        ArtistViewCommon.__init__(self)
        self._jump_button.hide()
        self.__overlay = Gtk.Overlay()
        self.__overlay.show()
        self.__overlay.add_overlay(self._banner)
        album_ids = App().albums.get_ids(artist_ids, genre_ids)
        self.__album_box = AlbumsBoxView(genre_ids,
                                         artist_ids,
                                         ViewType.MEDIUM |
                                         ViewType.SCROLLED |
                                         ViewType.NOT_ADAPTIVE)
        height = self._banner.default_height // 3
        self._banner.set_height(height)
        self.__album_box.set_margin_top(height)
        self.__album_box.populate([Album(id) for id in album_ids])
        self.__album_box.show()
        self.__overlay.add_overlay(self.__album_box)
        self.add(self.__overlay)

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
