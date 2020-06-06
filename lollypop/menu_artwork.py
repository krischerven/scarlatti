# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c)      2020 CodedOre
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

from gi.repository import Gtk, Gio, GLib, Pango

from gettext import gettext as _

from lollypop.widgets_artwork_artist import ArtistArtworkSearchWidget
from lollypop.widgets_artwork_album import AlbumArtworkSearchWidget

class ArtistArtworkMenu(Gtk.Bin):
    """
        A popover to change artwork
    """

    def __init__(self, artist_id, view_type):
        """
            Init popover
            @param artist_id as int
        """
        Gtk.Bin.__init__(self)
        self.__artist_id = artist_id
        self.view_type = view_type
        self.__artwork_search = ArtistArtworkSearchWidget(self.__artist_id,
                                                          self.view_type)
        self.__artwork_search.show()
        GLib.timeout_add(250, self.__artwork_search.populate)
        self.add(self.__artwork_search)

    @property
    def submenu_name(self):
        """
            Get submenu name
            @return str
        """
        return _("Change Artwork")

class AlbumArtworkMenu(Gtk.Bin):
    """
        A popover to change artwork
    """

    def __init__(self, artist_id, view_type):
        """
            Init popover
            @param artist_id as int
        """
        Gtk.Bin.__init__(self)
        self.__artist_id = artist_id
        self.view_type = view_type
        self.__artwork_search = AlbumArtworkSearchWidget(self.__artist_id,
                                                          self.view_type)
        self.__artwork_search.show()
        GLib.timeout_add(250, self.__artwork_search.populate)
        self.add(self.__artwork_search)

    @property
    def submenu_name(self):
        """
            Get submenu name
            @return str
        """
        return _("Change Artwork")
