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

from lollypop.define import ViewType
from lollypop.menu_playlists import PlaylistsMenu
from lollypop.menu_artist import ArtistMenu


class ToolbarMenu(Gio.Menu):
    """
        Contextual menu for toolbar
    """

    def __init__(self, track):
        """
            Init menu
            @param track as Track
        """
        Gio.Menu.__init__(self)
        if track.id >= 0:
            playlist_menu = PlaylistsMenu(track)
            self.insert_section(1, _("Playlists"), playlist_menu)
        self.insert_section(2, _("Artist"),
                            ArtistMenu(track, ViewType.ALBUM))
