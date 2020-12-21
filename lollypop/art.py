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

from gi.repository import Gio, GdkPixbuf, Gdk, GLib

from hashlib import md5

from lollypop.art_base import BaseArt
from lollypop.art_album import AlbumArt
from lollypop.art_artist import ArtistArt
from lollypop.art_downloader import DownloaderArt
from lollypop.logger import Logger
from lollypop.define import CACHE_PATH, ALBUMS_WEB_PATH, ALBUMS_PATH
from lollypop.define import ARTISTS_PATH, TimeStamp
from lollypop.define import App, StoreExtention
from lollypop.utils import emit_signal
from lollypop.utils_file import create_dir, remove_oldest


class Art(BaseArt, AlbumArt, ArtistArt, DownloaderArt):
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
        DownloaderArt.__init__(self)
        # Move old store
        # FIXME: Remove this later
        store = Gio.File.new_for_path(
            GLib.get_user_data_dir() + "/lollypop/store")
        if store.query_exists():
            new_store = Gio.File.new_for_path(ALBUMS_PATH)
            if not new_store.query_exists():
                store.move(new_store, Gio.FileCopyFlags.OVERWRITE, None, None)
        create_dir(CACHE_PATH)
        create_dir(ALBUMS_PATH)
        create_dir(ALBUMS_WEB_PATH)
        create_dir(ARTISTS_PATH)
        App().settings.connect("changed::hd-artwork",
                               self.__on_hd_artwork_changed)
        self.__on_hd_artwork_changed()

    def save_pixbuf(self, pixbuf, path):
        """
            Save pixbuf at path
            @param pixbuf as GdkPixbuf.Pixbuf
            @param path as str
        """
        if self._extension == StoreExtention.PNG:
            pixbuf.savev(path, "png", [None], [None])
        else:
            pixbuf.savev(path, "jpeg", ["quality"], ["100"])

    def add_extension(self, path):
        """
            Add file extension to path
            @param path as str
            @return str
        """
        if self._extension == StoreExtention.PNG:
            return "%s.png" % path
        else:
            return "%s.jpg" % path

    def add_artwork_to_cache(self, name, surface, prefix):
        """
            Add artwork to cache
            @param name as str
            @param surface as cairo.Surface
            @param prefix as str
            @thread safe
        """
        try:
            encoded = md5(name.encode("utf-8")).hexdigest()
            width = surface.get_width()
            height = surface.get_height()
            cache_path = "%s/@%s@%s_%s_%s" % (CACHE_PATH,
                                              prefix,
                                              encoded,
                                              width, height)
            pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
            self.save_pixbuf(pixbuf, self.add_extension(cache_path))
        except Exception as e:
            Logger.error("Art::add_artwork_to_cache(): %s" % e)

    def remove_artwork_from_cache(self, name, prefix):
        """
            Remove artwork from cache
            @param name as str
            @param prefix as str
        """
        try:
            from glob import glob
            encoded = md5(name.encode("utf-8")).hexdigest()
            if self._extension == StoreExtention.PNG:
                extension = "png"
            else:
                extension = "jpg"
            search = "%s/@%s@%s_*.%s" % (CACHE_PATH,
                                         prefix,
                                         encoded,
                                         extension)
            pathes = glob(search)
            for path in pathes:
                f = Gio.File.new_for_path(path)
                f.delete(None)
            emit_signal(self, "artwork-cleared", name, prefix)
        except Exception as e:
            Logger.error("Art::remove_artwork_from_cache(): %s" % e)

    def get_artwork_from_cache(self, name, prefix, width, height):
        """
            Get artwork from cache
            @param name as str
            @param prefix as str
            @param width as int
            @param height as int
            @return GdkPixbuf.Pixbuf
        """
        try:
            encoded = md5(name.encode("utf-8")).hexdigest()
            cache_path = "%s/@%s@%s_%s_%s" % (CACHE_PATH,
                                              prefix,
                                              encoded,
                                              width, height)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                self.add_extension(cache_path))
            return pixbuf
        except Exception as e:
            Logger.warning("Art::get_artwork_from_cache(): %s" % e)
            return None

    def artwork_exists_in_cache(self, name, prefix, width, height):
        """
            True if artwork exists in cache
            @param name as str
            @param prefix as str
            @param width as int
            @param height as int
            @return bool
        """
        encoded = md5(name.encode("utf-8")).hexdigest()
        cache_path = "%s/@%s@%s_%s_%s" % (CACHE_PATH,
                                          prefix,
                                          encoded,
                                          width, height)
        f = Gio.File.new_for_path(self.add_extension(cache_path))
        return f.query_exists()

    def clean_artwork(self):
        """
            Remove old artwork from disk
        """
        try:
            remove_oldest(CACHE_PATH, TimeStamp.ONE_YEAR)
            remove_oldest(ARTISTS_PATH, TimeStamp.THREE_YEAR)
            remove_oldest(ALBUMS_PATH, TimeStamp.THREE_YEAR)
            remove_oldest(ALBUMS_WEB_PATH, TimeStamp.ONE_YEAR)
        except Exception as e:
            Logger.error("Art::clean_artwork(): %s", e)

    def clean_rounded(self):
        """
            Clean rounded artwork
        """
        try:
            from pathlib import Path
            if self._extension == StoreExtention.PNG:
                extension = "png"
            else:
                extension = "jpg"
            for p in Path(CACHE_PATH).glob("@ROUNDED*@*.%s" % extension):
                p.unlink()
        except Exception as e:
            Logger.error("Art::clean_all_cache(): %s", e)

    def clean_all_cache(self):
        """
            Remove all covers from cache
        """
        try:
            from pathlib import Path
            if self._extension == StoreExtention.PNG:
                extension = "png"
            else:
                extension = "jpg"
            for p in Path(CACHE_PATH).glob("*.%s" % extension):
                p.unlink()
        except Exception as e:
            Logger.error("Art::clean_all_cache(): %s", e)

    def __on_hd_artwork_changed(self, *ignore):
        """
            Update extension value
        """
        if App().settings.get_value("hd-artwork"):
            self._extension = StoreExtention.PNG
        else:
            self._extension = StoreExtention.JPG
