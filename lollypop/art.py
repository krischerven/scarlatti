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

from gi.repository import Gio, GdkPixbuf, Gdk

from hashlib import md5

from lollypop.art_base import BaseArt
from lollypop.art_album import AlbumArt
from lollypop.art_artist import ArtistArt
from lollypop.art_radio import RadioArt
from lollypop.objects_album import Album
from lollypop.logger import Logger
from lollypop.downloader_art import ArtDownloader
from lollypop.define import CACHE_PATH, ALBUMS_WEB_PATH, ALBUMS_PATH
from lollypop.define import ARTISTS_PATH, ARTISTS_WEB_PATH
from lollypop.define import App, StorageType
from lollypop.utils import create_dir, emit_signal

from time import sleep
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
        create_dir(ALBUMS_PATH)
        create_dir(ALBUMS_WEB_PATH)
        create_dir(ARTISTS_PATH)
        create_dir(ARTISTS_WEB_PATH)

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
            cache_path_jpg = "%s/@%s@%s_%s_%s.jpg" % (CACHE_PATH,
                                                      prefix,
                                                      encoded,
                                                      width, height)
            pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
            pixbuf.savev(cache_path_jpg, "jpeg", ["quality"],
                         [str(App().settings.get_value(
                             "cover-quality").get_int32())])
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
            search = "%s/@%s@%s_*.jpg" % (CACHE_PATH,
                                          prefix,
                                          encoded)
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
            cache_path_jpg = "%s/@%s@%s_%s_%s.jpg" % (CACHE_PATH,
                                                      prefix,
                                                      encoded,
                                                      width, height)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path_jpg)
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
        cache_path_jpg = "%s/@%s@%s_%s_%s.jpg" % (CACHE_PATH,
                                                  prefix,
                                                  encoded,
                                                  width, height)
        f = Gio.File.new_for_path(cache_path_jpg)
        return f.query_exists()

    def clean_old_artwork(self):
        """
            Slow silent cleaner: web albums are removed from SQL queries
            so we may have unwanted artwork on disk
        """
        def cleaner():
            sleep(10)
            f = Gio.File.new_for_path(ALBUMS_PATH)
            infos = f.enumerate_children(
                                    "standard::name",
                                    Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                    None)
            # Get all files in store
            files = []
            for info in infos:
                sleep(0.1)
                f = infos.get_child(info)
                files.append(f.get_basename())
            infos.close(None)
            # Remove wanted files
            for storage_type in [StorageType.SAVED,
                                 StorageType.SPOTIFY_NEW_RELEASES,
                                 StorageType.SPOTIFY_SIMILARS]:
                for album_id in App().albums.get_for_storage_type(
                        storage_type):
                    sleep(0.1)
                    album = Album(album_id)
                    filename = self.get_album_cache_name(album) + ".jpg"
                    if filename in files:
                        files.remove(filename)
            # Delete remaining files
            for filename in files:
                sleep(1)
                store_path = ALBUMS_PATH + "/" + filename
                f = Gio.File.new_for_path(store_path)
                f.delete()

        App().task_helper.run(cleaner)

    def clean_web(self):
        """
            Remove all covers from cache
        """
        try:
            rmtree(ALBUMS_WEB_PATH)
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
