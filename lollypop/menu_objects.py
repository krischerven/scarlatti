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

from gi.repository import Gio

from gettext import gettext as _

from lollypop.define import ViewType, StorageType
from lollypop.menu_playlists import PlaylistsMenu
from lollypop.menu_artist import ArtistMenu
from lollypop.menu_edit import EditMenu
from lollypop.menu_playback import PlaybackMenu
from lollypop.menu_sync import SyncAlbumMenu


class AlbumMenu(Gio.Menu):
    """
        Contextual menu for album
    """

    def __init__(self, album, view_type):
        """
            Init menu model
            @param album as Album
            @param view_type as ViewType
        """
        Gio.Menu.__init__(self)
        self.append_section(_("Artist"),
                            ArtistMenu(album, view_type))
        section = Gio.Menu()
        if album.storage_type & (StorageType.COLLECTION | StorageType.SAVED):
            section.append_submenu(_("Playlists"), PlaylistsMenu(album))
        section.append_submenu(_("Devices"), SyncAlbumMenu(album))
        self.append_section(_("Add to"), section)
        self.append_section(_("Edit"), EditMenu(album))


class TrackMenu(Gio.Menu):
    """
        Contextual menu for a track
    """

    def __init__(self, track, show_artist=False):
        """
            Init menu model
            @param track as Track
            @param show artist menu as bool
        """
        Gio.Menu.__init__(self)
        if show_artist and not track.storage_type & StorageType.EPHEMERAL:
            self.append_section(_("Artist"), ArtistMenu(track, ViewType.ALBUM))
        self.append_section(_("Playback"), PlaybackMenu(track))
        if not track.storage_type & StorageType.EPHEMERAL:
            section = Gio.Menu()
            section.append_submenu(_("Playlists"), PlaylistsMenu(track))
        self.append_section(_("Add to"), section)
        self.append_section(_("Edit"), EditMenu(track))
