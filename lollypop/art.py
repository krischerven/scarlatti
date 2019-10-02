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

from gi.repository import Gio, GdkPixbuf, Gdk

from lollypop.art_base import BaseArt
from lollypop.art_album import AlbumArt
from lollypop.art_artist import ArtistArt
from lollypop.art_radio import RadioArt
from lollypop.logger import Logger
from lollypop.downloader_art import ArtDownloader
from lollypop.define import CACHE_PATH, TMP_PATH, STORE_PATH, App
from lollypop.utils import create_dir, escape

from shutil import rmtree


class Art(BaseArt, AlbumArt, ArtistArt, RadioArt, ArtDownloader):
    """
        Global artwork manager
    """

    def __init__(self):
        """
            Init artwork
        """
        BaseArt.__init__(self)
        AlbumArt.__init__(self)
        ArtistArt.__init__(self)
        RadioArt.__init__(self)
        ArtDownloader.__init__(self)
        create_dir(CACHE_PATH)
        create_dir(STORE_PATH)
        create_dir(TMP_PATH)

    def add_artwork_to_cache(self, name, surface):
        """
            Add artwork to cache
            @param name as str
            @param surface as cairo.Surface
            @thread safe
        """
        try:
            width = surface.get_width()
            height = surface.get_height()
            cache_path_jpg = "%s/@%s@_%s_%s.jpg" % (CACHE_PATH,
                                                    escape(name),
                                                    width, height)
            pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
            pixbuf.savev(cache_path_jpg, "jpeg", ["quality"],
                         [str(App().settings.get_value(
                             "cover-quality").get_int32())])
        except Exception as e:
            Logger.error("Art::add_artwork_to_cache(): %s" % e)

    def remove_artwork_from_cache(self, name):
        """
            Remove artwork from cache
            @param name as str
        """
        try:
            from glob import glob
            search = "%s/@%s@_*.jpg" % (CACHE_PATH, escape(name))
            pathes = glob(search)
            for path in pathes:
                f = Gio.File.new_for_path(path)
                f.delete(None)
        except Exception as e:
            Logger.error("Art::remove_artwork_from_cache(): %s" % e)

    def get_artwork_from_cache(self, name, width, height):
        """
            Get artwork from cache
            @param name as str
            @param width as int
            @param height as int
            @return GdkPixbuf.Pixbuf
        """
        try:
            cache_path_jpg = "%s/@%s@_%s_%s.jpg" % (CACHE_PATH,
                                                    escape(name),
                                                    width, height)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path_jpg)
            return pixbuf
        except Exception as e:
            Logger.warning("Art::get_artwork_from_cache(): %s" % e)
            return None

    def artwork_exists_in_cache(self, name, width, height):
        """
            True if artwork exists in cache
            @param name as str
            @param width as int
            @param height as int
            @return bool
        """
        cache_path_jpg = "%s/@%s@_%s_%s.jpg" % (CACHE_PATH,
                                                escape(name),
                                                width, height)
        f = Gio.File.new_for_path(cache_path_jpg)
        return f.query_exists()

    def clean_web(self):
        """
            Remove all covers from cache
        """
        try:
            rmtree(TMP_PATH)
        except Exception as e:
            Logger.error("Art::clean_web(): %s", e)

    def clean_rounded(self):
        """
            Clean rounded artwork
        """
        try:
            from pathlib import Path
            for p in Path(CACHE_PATH).glob("@ROUNDED*@*.jpg"):
                p.unlink()
        except Exception as e:
            Logger.error("Art::clean_all_cache(): %s", e)

    def clean_all_cache(self):
        """
            Remove all covers from cache
        """
        try:
            from pathlib import Path
            for p in Path(CACHE_PATH).glob("*.jpg"):
                p.unlink()
        except Exception as e:
            Logger.error("Art::clean_all_cache(): %s", e)
