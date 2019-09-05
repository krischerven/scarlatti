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

from gi.repository import Gio, GObject

from gettext import gettext as _

from lollypop.logger import Logger
from lollypop.widgets_artwork import ArtworkSearchWidget, ArtworkSearchChild
from lollypop.define import App, Type


class AlbumArtworkSearchWidget(ArtworkSearchWidget):
    """
        Search for album artwork
    """

    __gsignals__ = {
        "closed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, album, view_type):
        """
            Init search
            @param album as Album
            @param view_type as ViewType
        """
        ArtworkSearchWidget.__init__(self, view_type)
        self.__album = album

    def populate(self):
        """
            Populate view
        """
        try:
            ArtworkSearchWidget.populate(self)
            # First load local files
            uris = App().art.get_album_artworks(self.__album)
            # Direct load, not using loopback because not many items
            for uri in uris:
                child = ArtworkSearchChild(_("Local"))
                child.show()
                f = Gio.File.new_for_uri(uri)
                (status, content, tag) = f.load_contents()
                if status:
                    status = child.populate(content)
                if status:
                    self._flowbox.add(child)
        except Exception as e:
            Logger.error("AlbumArtworkSearchWidget::populate(): %s", e)

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
                App().art.save_album_artwork(data, self.__album)
            self._streams = {}
        except Exception as e:
            Logger.error(
                "AlbumArtworkSearchWidget::_save_from_filename(): %s" % e)

    def _get_current_search(self):
        """
            Return current searches
            @return str
        """
        search = ArtworkSearchWidget._get_current_search(self)
        if search != "":
            pass
        else:
            is_compilation = self.__album.artist_ids and\
                self.__album.artist_ids[0] == Type.COMPILATIONS
            if is_compilation:
                search = self.__album.name
            else:
                search = "%s+%s" % (self.__album.artists[0], self.__album.name)
        return search

    def _search_from_downloader(self):
        """
            Load artwork from downloader
        """
        is_compilation = self.__album.artist_ids and\
            self.__album.artist_ids[0] == Type.COMPILATIONS
        if is_compilation:
            artist = "Compilation"
        else:
            artist = self.__album.artists[0]
        App().task_helper.run(
                App().art.search_album_artworks,
                artist,
                self.__album.name,
                self._cancellable)

    def _on_activate(self, flowbox, child):
        """
            Save artwork
            @param flowbox as Gtk.FlowBox
            @param child as ArtworkSearchChild
        """
        try:
            if isinstance(child, ArtworkSearchChild):
                App().art.save_album_artwork(child.bytes, self.__album)
                self._streams = {}
            else:
                App().art.remove_album_artwork(self.__album)
                App().art.save_album_artwork(None, self.__album)
                App().art.clean_album_cache(self.__album)
                App().art.emit("album-artwork-changed", self.__album.id)
            self.emit("closed")
        except Exception as e:
            Logger.error("AlbumArtworkSearchWidget::_on_activate(): %s", e)
