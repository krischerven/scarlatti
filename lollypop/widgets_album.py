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

from lollypop.define import App
from lollypop.helper_signals import SignalsHelper, signals


class AlbumWidget(SignalsHelper):
    """
        Album widget
    """

    @signals
    def __init__(self, album, genre_ids, artist_ids):
        """
            Init Album widget
            @param album as Album
            @param genre_ids as [int]
            @param artist_ids as [int]
        """
        self._artwork = None
        self._album = album
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
        return [
            (App().scanner, "album-updated", "_on_album_updated")
        ]

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        if self._artwork is None:
            return
        selected = self._album.id == App().player.current_track.album.id
        if selected:
            self._artwork.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self._artwork.set_state_flags(Gtk.StateFlags.NORMAL, True)

    @property
    def album(self):
        """
            @return Album
        """
        return self._album

#######################
# PROTECTED           #
#######################
    def _on_album_updated(self, scanner, album_id, destroy):
        pass
