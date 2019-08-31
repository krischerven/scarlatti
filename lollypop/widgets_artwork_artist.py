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

from lollypop.logger import Logger
from lollypop.widgets_artwork import ArtworkSearchWidget, ArtworkSearchChild
from lollypop.define import App


class ArtistArtworkSearchWidget(ArtworkSearchWidget):
    """
        Search for artist artwork
    """

    def __init__(self, artist_id):
        """
            Init search
            @param artist_id as int
        """
        ArtworkSearchWidget.__init__(self)
        self.__artist = App().artists.get_name(artist_id)

#######################
# PROTECTED           #
#######################
    def _save_from_filename(self, filename):
        """
            Save filename as album artwork
            @param button as Gtk.button
        """
        try:
            f = Gio.File.new_for_path(filename)
            (status, data, tag) = f.load_contents()
            if status:
                App().art.add_artist_artwork(self.__artist, data)
            self._streams = {}
        except Exception as e:
            Logger.error(
                "ArtistArtworkSearchWidget::_save_from_filename(): %s" % e)

    def _on_reset_confirm(self, button):
        """
            Reset artwork
            @param button as Gtk.Button
        """
        ArtworkSearchWidget._on_reset_confirm(self, button)
        App().art.add_artist_artwork(self.__artist, None)

    def _get_current_search(self):
        """
            Return current searches
            @return str
        """
        search = ArtworkSearchWidget._get_current_search(self)
        if search != "":
            pass
        else:
            search = self.__artist
        return search

    def _search_from_downloader(self):
        """
            Load artwork from downloader
        """
        App().task_helper.run(
                App().art.search_artist_artwork,
                self.__artist,
                self._cancellable)

    def _on_activate(self, flowbox, child):
        """
            Save artwork
            @param flowbox as Gtk.FlowBox
            @param child as ArtworkSearchChild
        """
        try:
            if isinstance(child, ArtworkSearchChild):
                self._close_popover()
                App().art.add_artist_artwork(self.__artist, child.bytes)
                self._streams = {}
            else:
                ArtworkSearchWidget._on_activate(self, flowbox, child)
        except Exception as e:
            Logger.error("ArtistArtworkSearchWidget::_on_activate(): %s", e)
