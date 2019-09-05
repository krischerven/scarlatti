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

from gi.repository import GLib

from lollypop.define import App, Type
from lollypop.widgets_albums_rounded import RoundedAlbumsWidget
from lollypop.objects_album import Album


class AlbumsGenreWidget(RoundedAlbumsWidget):
    """
        Genre widget showing cover for 4 albums
    """

    def __init__(self, genre_id, view_type, font_height):
        """
            Init widget
            @param Genre as [int]
            @param view_type as ViewType
            @param font_height as int
        """
        self.__font_height = font_height
        name = sortname = App().genres.get_name(genre_id)
        RoundedAlbumsWidget.__init__(self, genre_id, name, sortname, view_type)
        self._genre = Type.GENRES

    def populate(self):
        """
            Populate widget content
        """
        if self._artwork is None:
            RoundedAlbumsWidget.populate(self)
        else:
            self.set_artwork()

    def set_view_type(self, view_type):
        """
            Update view type
            @param view_type as ViewType
        """
        RoundedAlbumsWidget.set_view_type(self, view_type)
        self.set_size_request(self._art_size,
                              self._art_size + self.__font_height)

    @property
    def artwork_name(self):
        """
            Get artwork name
            return str
        """
        return "genre_" + self.name

#######################
# PROTECTED           #
#######################
    def _get_album_ids(self):
        """
            Get album ids
            @return [int]
        """
        return App().albums.get_ids([], [self._data])

    def _on_play_clicked(self, button):
        """
            Play decade
            @param button as Gtk.Button
        """
        if App().player.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        albums = [Album(album_id) for album_id in self._get_album_ids()]
        App().player.play_albums(albums)
