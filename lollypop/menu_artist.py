# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

from gettext import gettext as _

from lollypop.menu_sync import SyncAlbumsMenu
from lollypop.menu_playlists import PlaylistsMenu
from lollypop.define import App, ViewType, Type
from lollypop.objects_album import Album
from lollypop.utils import get_default_storage_type


class ArtistMenu(Gio.Menu):
    """
        Contextual menu for artist
    """
    def __init__(self, artist_id, storage_type, view_type, header=False):
        """
            Init artist menu
            @param artist_id as int
            @param storage_type as StorageType
            @param view_type as ViewType
            @param header as bool
        """
        Gio.Menu.__init__(self)
        if header:
            from lollypop.menu_header import ArtistMenuHeader
            self.append_item(ArtistMenuHeader(artist_id))
        if not view_type & ViewType.BANNER:
            from lollypop.menu_playback import ArtistPlaybackMenu
            self.append_section(_("Playback"),
                                ArtistPlaybackMenu(artist_id, storage_type))
        menu = ArtistAlbumsMenu(artist_id, view_type)
        self.append_section(_("Artist"), menu)
        storage_type = get_default_storage_type()
        album_ids = App().albums.get_ids([artist_id], [], storage_type, True)
        albums = [Album(album_id) for album_id in album_ids]
        self.append_submenu(_("Devices"), SyncAlbumsMenu(albums))
        self.append_submenu(_("Playlists"), PlaylistsMenu(albums))


class ArtistAlbumsMenu(Gio.Menu):
    """
        Contextual menu for artist albums
    """

    def __init__(self, artist_id, view_type):
        """
            Init artist albums menu
            @param artist id as int
            @param view_type as ViewType
        """
        Gio.Menu.__init__(self)
        self.__artist_id = artist_id
        self.__set_actions(view_type)

#######################
# PRIVATE             #
#######################
    def __set_actions(self, view_type):
        """
            Set artist actions
            @param view_type as ViewType
        """
        go_artist_action = Gio.SimpleAction(name="go_artist_action")
        App().add_action(go_artist_action)
        go_artist_action.connect("activate",
                                 self.__on_go_to_artist_activate)
        self.append(_("Available albums"), "app.go_artist_action")

    def __on_go_to_artist_activate(self, action, variant):
        """
            Show albums from artists
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_view([Type.ARTISTS],
                                         [self.__artist_id])
