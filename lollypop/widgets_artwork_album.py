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

from gi.repository import Gio, GObject, Gtk

from gettext import gettext as _

from lollypop.logger import Logger
from lollypop.utils import emit_signal
from lollypop.widgets_artwork import ArtworkSearchWidget, ArtworkSearchChild
from lollypop.define import App, Type, ViewType, MARGIN, MARGIN_SMALL
from lollypop.define import ArtBehaviour, ArtSize


class AlbumArtworkSearchWidget(ArtworkSearchWidget):
    """
        Search for album artwork
    """

    __gsignals__ = {
        "hidden": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self, album, view_type):
        """
            Init search
            @param album as Album
            @param view_type as ViewType
        """
        ArtworkSearchWidget.__init__(self, view_type)
        self.__album = album
        if view_type & ViewType.ADAPTIVE:
            self.set_row_spacing(MARGIN)
            self.set_margin_start(MARGIN_SMALL)
            self.set_margin_end(MARGIN_SMALL)
            self.set_margin_top(MARGIN)
            self.set_margin_bottom(MARGIN)
            button = Gtk.ModelButton.new()
            button.set_alignment(0, 0.5)
            button.connect("clicked",
                           lambda x: emit_signal(self, "hidden", True))
            button.show()
            label = Gtk.Label.new()
            label.show()
            self.__artwork = Gtk.Image.new()
            name = "<span alpha='40000'>%s</span>" % album.name
            App().art_helper.set_album_artwork(
                                            album,
                                            ArtSize.SMALL,
                                            ArtSize.SMALL,
                                            self.__artwork.get_scale_factor(),
                                            ArtBehaviour.CACHE |
                                            ArtBehaviour.CROP_SQUARE,
                                            self.__on_album_artwork)
            self.__artwork.show()
            label.set_markup(name)
            grid = Gtk.Grid()
            grid.set_column_spacing(MARGIN)
            grid.add(self.__artwork)
            grid.add(label)
            button.set_image(grid)
            button.get_style_context().add_class("padding")
            self.insert_row(0)
            self.attach(button, 0, 0, 1, 1)

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
                child = ArtworkSearchChild(_("Local"), self._view_type)
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
                App().task_helper.run(App().art.save_album_artwork,
                                      data, self.__album)
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
                App().task_helper.run(App().art.save_album_artwork,
                                      child.bytes, self.__album)
            else:
                App().art.remove_album_artwork(self.__album)
                App().art.save_album_artwork(None, self.__album)
                App().art.clean_album_cache(self.__album)
                emit_signal(App().art, "album-artwork-changed",
                            self.__album.id)
            emit_signal(self, "hidden", True)
        except Exception as e:
            Logger.error("AlbumArtworkSearchWidget::_on_activate(): %s", e)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is None:
            self.__artwork.set_from_icon_name("folder-music-symbolic",
                                              Gtk.IconSize.BUTTON)
        else:
            self.__artwork.set_from_surface(surface)
            del surface
