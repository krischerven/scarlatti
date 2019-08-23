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

from gi.repository import Gtk, Gio

from gettext import gettext as _

from lollypop.logger import Logger
from lollypop.widgets_artwork import ArtworkSearchWidget, ArtworkSearchChild
from lollypop.define import App, Type


class AlbumArtworkSearchWidget(ArtworkSearchWidget):
    """
        Search for album artwork
    """

    def __init__(self, album):
        """
            Init search
            @param album as Album
        """
        ArtworkSearchWidget.__init__(self)
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
    def _on_button_clicked(self, button):
        """
            Show file chooser
            @param button as Gtk.button
        """
        dialog = Gtk.FileChooserDialog()
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_buttons(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_transient_for(App().window)
        self._close_popover()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                f = Gio.File.new_for_path(dialog.get_filename())
                (status, data, tag) = f.load_contents()
                if status:
                    App().art.save_album_artwork(data, self.__album)
                self._streams = {}
            except Exception as e:
                Logger.error(
                    "AlbumArtworkSearchWidget::_on_button_clicked(): %s" % e)
        dialog.destroy()

    def _on_reset_confirm(self, button):
        """
            Reset artwork
            @param button as Gtk.Button
        """
        ArtworkSearchWidget._on_reset_confirm(self, button)
        App().art.remove_album_artwork(self.__album)
        App().art.save_album_artwork(None, self.__album)
        App().art.clean_album_cache(self.__album)
        App().art.emit("album-artwork-changed", self.__album.id)

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
                self._close_popover()
                App().art.save_album_artwork(child.bytes, self.__album)
                self._streams = {}
            else:
                ArtworkSearchWidget._on_activate(self, flowbox, child)
        except Exception as e:
            Logger.error("AlbumArtworkSearchWidget::_on_activate(): %s", e)
