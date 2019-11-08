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

from gi.repository import GLib, GdkPixbuf, Gio

from hashlib import md5

from lollypop.define import ArtBehaviour, ArtSize
from lollypop.define import CACHE_PATH
from lollypop.logger import Logger
from lollypop.utils import escape, emit_signal


class ArtistArt:
    """
         Manage artist artwork
         Should be inherited by a BaseArt
    """

    _INFO_PATH = GLib.get_user_data_dir() + "/lollypop/info"

    def __init__(self):
        """
            Init album art
        """
        try:
            d = Gio.File.new_for_path(self._INFO_PATH)
            if not d.query_exists():
                d.make_directory_with_parents()
        except:
            Logger.info("Can't create %s" % self._INFO_PATH)

    def artist_artwork_exists(self, artist):
        """
            True if artist artwork exists
            @param artist as str
            @return (bool, path)
        """
        escaped_artist = escape(artist)
        # Search in store
        paths = ["%s/%s.jpg" % (
                 self._INFO_PATH,
                 escaped_artist),
                 "%s/web_%s.jpg" % (
                 self._INFO_PATH,
                 escaped_artist)]
        for path in paths:
            if GLib.file_test(path, GLib.FileTest.EXISTS):
                return (True, path)
        return (False, None)

    def add_artist_artwork(self, artist, data, is_web=False):
        """
            Add artist artwork to store
            @param artist as str
            @param data as bytes
            @param is_web as bool
            @thread safe
        """
        self.uncache_artist_artwork(artist)
        if is_web:
            filepath = "%s/web_%s.jpg" % (self._INFO_PATH,
                                          escape(artist))
        else:
            filepath = "%s/%s.jpg" % (self._INFO_PATH,
                                      escape(artist))
        if data is None:
            f = Gio.File.new_for_path(filepath)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            fstream.close()
        else:
            bytes = GLib.Bytes.new(data)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
            stream.close()
            pixbuf.savev(filepath, "jpeg", ["quality"], ["100"])
        emit_signal(self, "artist-artwork-changed", artist)

    def get_artist_artwork(self, artist, width, height, scale_factor,
                           behaviour=ArtBehaviour.CACHE):
        """
            Return a cairo surface for album_id, covers are cached as jpg.
            @param artist as str
            @param width as int
            @param height as int
            @param scale_factor as int
            @param behaviour as ArtBehaviour
            @return cairo surface
            @thread safe
        """
        width *= scale_factor
        height *= scale_factor
        # Blur when reading from tags can be slow, so prefer cached version
        # Blur allows us to ignore width/height until we want CROP/CACHE
        optimized_blur = behaviour & (ArtBehaviour.BLUR |
                                      ArtBehaviour.BLUR_HARD) and\
            not behaviour & (ArtBehaviour.CACHE |
                             ArtBehaviour.CROP |
                             ArtBehaviour.CROP_SQUARE)
        if optimized_blur:
            w = ArtSize.BANNER * scale_factor
            h = ArtSize.BANNER * scale_factor
        else:
            w = width
            h = height
        filename = self.get_artist_cache_name(artist)
        cache_path_jpg = "%s/%s_%s_%s.jpg" % (CACHE_PATH, filename, w, h)
        pixbuf = None
        try:
            # Look in cache
            f = Gio.File.new_for_path(cache_path_jpg)
            if not behaviour & ArtBehaviour.NO_CACHE and f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path_jpg)
                if optimized_blur:
                    pixbuf = self.load_behaviour(pixbuf, None,
                                                 width, height, behaviour)
                return pixbuf
            else:
                (exists, path) = self.artist_artwork_exists(artist)
                if exists:
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                    except:
                        return None
                else:
                    self.cache_artist_artwork(artist)
                    return None
                pixbuf = self.load_behaviour(pixbuf, cache_path_jpg,
                                             width, height, behaviour)
            return pixbuf
        except Exception as e:
            Logger.error("ArtistArt::get_artist_artwork(): %s" % e)
            return None

    def get_artist_cache_name(self, artist):
        """
            Get a uniq string for artist
            @param artist as str
        """
        return md5(artist.encode("utf-8")).hexdigest()

    def uncache_artist_artwork(self, artist):
        """
            Remove artwork from cache
            @param artist as str
        """
        try:
            from pathlib import Path
            search = "%s*.jpg" % self.get_artist_cache_name(artist)
            for p in Path(CACHE_PATH).glob(search):
                p.unlink()
        except Exception as e:
            Logger.error("ArtistArt::uncache_artist_artwork(): %s" % e)

#######################
# PRIVATE             #
#######################
