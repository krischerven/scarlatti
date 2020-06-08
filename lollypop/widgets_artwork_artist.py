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

from lollypop.logger import Logger
from lollypop.utils import emit_signal
from lollypop.widgets_artwork import ArtworkSearchWidget, ArtworkSearchChild
from lollypop.define import App, ViewType, ArtSize, ArtBehaviour, MARGIN
from lollypop.define import MARGIN_SMALL, StorageType


class ArtistArtworkSearchWidget(ArtworkSearchWidget):
    """
        Search for artist artwork
    """

    __gsignals__ = {
        "hidden": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self, artist_id, view_type, in_menu=False):
        """
            Init search
            @param artist_id as int
            @param view_type as ViewType
        """
        ArtworkSearchWidget.__init__(self, view_type)
        self.__artist = App().artists.get_name(artist_id)
        if view_type & ViewType.ADAPTIVE and not in_menu:
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
            name = "<span alpha='40000'>%s</span>" % self.__artist
            App().art_helper.set_artist_artwork(
                                       self.__artist,
                                       ArtSize.SMALL,
                                       ArtSize.SMALL,
                                       self.__artwork.get_scale_factor(),
                                       ArtBehaviour.ROUNDED |
                                       ArtBehaviour.CROP_SQUARE |
                                       ArtBehaviour.CACHE,
                                       self.__on_artist_artwork)
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
                App().art.add_artist_artwork(self.__artist, data,
                                             StorageType.COLLECTION)
        except Exception as e:
            Logger.error(
                "ArtistArtworkSearchWidget::_save_from_filename(): %s" % e)

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
                App().task_helper.run(App().art.add_artist_artwork,
                                      self.__artist, child.bytes,
                                      StorageType.COLLECTION)
            else:
                App().task_helper.run(App().art.add_artist_artwork,
                                      self.__artist, None,
                                      StorageType.COLLECTION)
            emit_signal(self, "hidden", True)
        except Exception as e:
            Logger.error("ArtistArtworkSearchWidget::_on_activate(): %s", e)

    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__artwork.get_style_context().add_class("circle-icon")
            self.__artwork.set_size_request(ArtSize.SMALL, ArtSize.SMALL)
            self.__artwork.set_from_icon_name("avatar-default-symbolic",
                                              Gtk.IconSize.BUTTON)
        else:
            self.__artwork.get_style_context().remove_class("circle-icon")
            self.__artwork.set_from_surface(surface)
            del surface
