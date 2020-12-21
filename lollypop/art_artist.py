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

from gi.repository import GLib, GdkPixbuf, Gio

from hashlib import md5

from lollypop.define import ArtBehaviour, ArtSize
from lollypop.define import CACHE_PATH, ARTISTS_PATH, StoreExtention
from lollypop.logger import Logger
from lollypop.utils import emit_signal


class ArtistArt:
    """
         Manage artist artwork
         Should be inherited by a BaseArt
    """

    def __init__(self):
        """
            Init artist artwork
        """
        pass

    def get_artist_artwork_path(self, artist):
        """
            True if artist artwork exists
            @param artist as str
            @return str/None
        """
        encoded = self.encode_artist_name(artist)
        if self._extension == StoreExtention.PNG:
            extensions = ["png", "jpg"]
        else:
            extensions = ["jpg", "png"]
        for extension in extensions:
            cache_path = "%s/%s.%s" % (ARTISTS_PATH, encoded, extension)
            if GLib.file_test(cache_path, GLib.FileTest.EXISTS):
                return cache_path
        return None

    def add_artist_artwork(self, artist, data, storage_type):
        """
            Add artist artwork to store
            @param artist as str
            @param data as bytes
            @param storage_type as StorageType
            @thread safe
        """
        self.uncache_artist_artwork(artist)
        encoded = self.encode_artist_name(artist)
        cache_path = "%s/%s" % (ARTISTS_PATH, encoded)
        cache_path = self.add_extension(cache_path)
        if data is None:
            f = Gio.File.new_for_path(cache_path)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            fstream.close()
        else:
            bytes = GLib.Bytes.new(data)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
            stream.close()
            self.save_pixbuf(pixbuf, cache_path)
        emit_signal(self, "artist-artwork-changed", artist)

    def get_artist_artwork(self, artist, width, height, scale_factor,
                           behaviour=ArtBehaviour.CACHE):
        """
            Return a cairo surface for album_id
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
        filename = self.encode_artist_name(artist)
        cache_path = "%s/%s_%s_%s" % (CACHE_PATH, filename, w, h)
        cache_path = self.add_extension(cache_path)
        pixbuf = None
        try:
            # Look in cache
            f = Gio.File.new_for_path(cache_path)
            if not behaviour & ArtBehaviour.NO_CACHE and f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path)
                if optimized_blur:
                    pixbuf = self.load_behaviour(pixbuf,
                                                 width, height, behaviour)
                return pixbuf
            else:
                cache_path = self.get_artist_artwork_path(artist)
                if cache_path is not None:
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path)
                    except:
                        return None
                else:
                    self.cache_artist_artwork(artist)
                    return None
                pixbuf = self.load_behaviour(pixbuf,
                                             width, height, behaviour)
                if behaviour & ArtBehaviour.CACHE:
                    self.save_pixbuf(pixbuf, cache_path)
            return pixbuf
        except Exception as e:
            Logger.error("ArtistArt::get_artist_artwork(): %s" % e)
            return None

    def encode_artist_name(self, artist):
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
            if self._extension == StoreExtention.PNG:
                extension = "png"
            else:
                extension = "jpg"
            search = "%s*.%s" % (self.encode_artist_name(artist), extension)
            for p in Path(CACHE_PATH).glob(search):
                p.unlink()
        except Exception as e:
            Logger.error("ArtistArt::uncache_artist_artwork(): %s" % e)

#######################
# PRIVATE             #
#######################
