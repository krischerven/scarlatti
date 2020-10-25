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

from gi.repository import GLib, GdkPixbuf, Gio, Gst

from random import choice
from gettext import gettext as _
from time import time

from lollypop.tagreader import Discoverer
from lollypop.define import App, ArtSize, ArtBehaviour, StorageType
from lollypop.define import CACHE_PATH, ALBUMS_WEB_PATH, ALBUMS_PATH
from lollypop.logger import Logger
from lollypop.utils_file import is_readonly
from lollypop.utils import emit_signal
from lollypop.helper_task import TaskHelper


class AlbumArt:
    """
         Manager album artwork
         Should be inherited by a BaseArt
    """

    _MIMES = ("jpeg", "jpg", "png", "gif")

    def __init__(self):
        """
            Init album art
        """
        self._ext = "jpg"
        self.__favorite = App().settings.get_value(
            "favorite-cover").get_string()
        if not self.__favorite:
            self.__favorite = App().settings.get_default_value(
                "favorite-cover").get_string()

    def get_album_cache_path(self, album, width, height):
        """
            get artwork cache path for album_id
            @param album as Album
            @param width as int
            @param height as int
            @return cover path as string or None if no cover
        """
        try:
            cache_filepath = "%s/%s_%s_%s.%s" % (CACHE_PATH,
                                                 album.lp_album_id,
                                                 width,
                                                 height,
                                                 self._ext)
            f = Gio.File.new_for_path(cache_filepath)
            if f.query_exists():
                return cache_filepath
            else:
                self.get_album_artwork(album, width, height, 1)
                if f.query_exists():
                    return cache_filepath
        except Exception as e:
            Logger.error("Art::get_album_cache_path(): %s" % e)
        return None

    def get_album_artwork_uri(self, album):
        """
            Look for artwork in dir:
            - favorite from settings first
            - Artist_Album.jpg then
            - Any any supported image otherwise
            @param album as Album
            @return cover uri as string
        """
        if album.id is None:
            return None
        try:
            self.__update_album_uri(album)
            if not album.storage_type & StorageType.COLLECTION:
                store_path = "%s/%s.jpg" % (ALBUMS_WEB_PATH, album.lp_album_id)
                uris = [GLib.filename_to_uri(store_path)]
            else:
                store_path = "%s/%s.jpg" % (ALBUMS_PATH, album.lp_album_id)
                uris = [
                    # Default favorite artwork
                    "%s/%s" % (album.uri, self.__favorite),
                    # Used when album.uri is readonly or for Web
                    GLib.filename_to_uri(store_path),
                    # Used when having muliple albums in same folder
                    "%s/%s.jpg" % (album.uri, album.lp_album_id)
                ]
            for uri in uris:
                f = Gio.File.new_for_uri(uri)
                if f.query_exists():
                    return uri
        except Exception as e:
            Logger.error("AlbumArt::get_album_artwork_uri(): %s", e)
        return None

    def get_first_album_artwork(self, album):
        """
            Get first locally available artwork for album
            @param album as Album
            @return path or None
        """
        # Folders with many albums, get_album_artwork_uri()
        if App().albums.get_uri_count(album.uri) > 1:
            return None
        if not album.storage_type & (StorageType.COLLECTION |
                                     StorageType.EXTERNAL):
            return None
        f = Gio.File.new_for_uri(album.uri)
        infos = f.enumerate_children("standard::name",
                                     Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                     None)
        all_uris = []
        for info in infos:
            f = infos.get_child(info)
            all_uris.append(f.get_uri())
        for uri in filter(lambda p: p.lower().endswith(self._MIMES), all_uris):
            return uri
        infos.close(None)
        return None

    def get_album_artworks(self, album):
        """
            Get locally available artworks for album
            @param album as Album
            @return [paths]
        """
        if not album.storage_type & (StorageType.COLLECTION |
                                     StorageType.EXTERNAL):
            return []
        try:
            uris = []
            f = Gio.File.new_for_uri(album.uri)
            infos = f.enumerate_children(
                "standard::name",
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            all_uris = []
            for info in infos:
                f = infos.get_child(info)
                all_uris.append(f.get_uri())
            for uri in filter(lambda p: p.lower().endswith(self._MIMES),
                              all_uris):
                uris.append(uri)
            infos.close(None)
        except Exception as e:
            Logger.error("AlbumArt::get_album_artworks(): %s", e)
        return uris

    def get_album_artwork(self, album, width, height, scale_factor,
                          behaviour=ArtBehaviour.CACHE |
                          ArtBehaviour.CROP_SQUARE):
        """
            Return a cairo surface for album_id, covers are cached as jpg.
            @param album as Album
            @param width as int
            @param height as int
            @param scale_factor factor as int
            @param behaviour as ArtBehaviour
            @return cairo surface
            @thread safe
        """
        uri = None
        if album.id is None:
            return None
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
            w = ArtSize.BIG * scale_factor
            h = ArtSize.BIG * scale_factor
        else:
            w = width
            h = height
        cache_filepath = "%s/%s_%s_%s.%s" % (CACHE_PATH, album.lp_album_id,
                                             w, h, self._ext)
        pixbuf = None
        try:
            # Look in cache
            f = Gio.File.new_for_path(cache_filepath)
            if not behaviour & ArtBehaviour.NO_CACHE and f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_filepath)
                if optimized_blur:
                    pixbuf = self.load_behaviour(pixbuf, None,
                                                 width, height, behaviour)

            # Use favorite folder artwork
            if pixbuf is None:
                uri = self.get_album_artwork_uri(album)
                data = None
                if uri is not None:
                    f = Gio.File.new_for_uri(uri)
                    (status, data, tag) = f.load_contents(None)
                    bytes = GLib.Bytes.new(data)
                    stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream(
                        stream, None)
                    stream.close()

            # Use tags artwork
            if pixbuf is None and album.tracks and\
                    album.storage_type & (StorageType.COLLECTION |
                                          StorageType.EXTERNAL):
                try:
                    track = choice(album.tracks)
                    pixbuf = self.pixbuf_from_tags(track.uri)
                except Exception as e:
                    Logger.error("AlbumArt::get_album_artwork(): %s", e)

            # Use folder artwork
            if pixbuf is None and\
                    album.storage_type & (StorageType.COLLECTION |
                                          StorageType.EXTERNAL):
                uri = self.get_first_album_artwork(album)
                # Look in album folder
                if uri is not None:
                    f = Gio.File.new_for_uri(uri)
                    (status, data, tag) = f.load_contents(None)
                    bytes = GLib.Bytes.new(data)
                    stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream(
                        stream, None)
                    stream.close()
            if pixbuf is None:
                self.cache_album_artwork(album.id)
                return None
            pixbuf = self.load_behaviour(pixbuf, cache_filepath,
                                         width, height, behaviour)
            return pixbuf
        except Exception as e:
            Logger.error("AlbumArt::get_album_artwork(): %s -> %s" % (uri, e))
            return None

    def add_album_artwork(self, album, data):
        """
            Save artwork for album
            @param data as bytes
            @param album as Album
        """
        try:
            if not album.storage_type & StorageType.COLLECTION:
                self.__save_web_album_artwork(album, data)
            elif is_readonly(album.uri):
                self.__save_ro_album_artwork(album, data)
            else:
                self.__add_album_artwork(album, data)
        except Exception as e:
            Logger.error("AlbumArt::add_album_artwork(): %s" % e)

    def move_artwork(self, old_lp_album_id, new_lp_album_id):
        """
            Move artwork when lp_album_id changed
            @param old_lp_album_id as str
            @param new_lp_album_id s str
        """
        try:
            for store in [ALBUMS_WEB_PATH, ALBUMS_PATH]:
                old_path = "%s/%s.jpg" % (store, old_lp_album_id)
                old = Gio.File.new_for_path(old_path)
                if old.query_exists():
                    new_path = "%s/%s.jpg" % (store, new_lp_album_id)
                    new = Gio.File.new_for_path(new_path)
                    old.move(new, Gio.FileCopyFlags.OVERWRITE, None, None)
                    break
        except Exception as e:
            Logger.error("AlbumArt::move_artwork(): %s" % e)

    def album_artwork_update(self, album_id):
        """
            Announce album cover update
            @param album_id as int
        """
        if album_id is not None:
            emit_signal(self, "album-artwork-changed", album_id)

    def remove_album_artwork(self, album):
        """
            Remove album artwork
            @param album as Album
        """
        for uri in self.get_album_artworks(album):
            f = Gio.File.new_for_uri(uri)
            try:
                f.trash()
            except Exception as e:
                Logger.error("AlbumArt::remove_album_artwork(): %s" % e)
                try:
                    f.delete(None)
                except Exception as e:
                    Logger.error("AlbumArt::remove_album_artwork(): %s" % e)
        self.__write_image_to_tags("", album)

    def clean_album_cache(self, album, width=-1, height=-1):
        """
            Remove cover from cache for album id
            @param album as Album
            @param width as int
            @param height as int
        """
        try:
            from pathlib import Path
            if width == -1 or height == -1:
                for p in Path(CACHE_PATH).glob("%s*.jpg" % album.lp_album_id):
                    p.unlink()
            else:
                filename = "%s/%s_%s_%s.jpg" % (CACHE_PATH,
                                                album.lp_album_id,
                                                width,
                                                height)
                f = Gio.File.new_for_path(filename)
                if f.query_exists():
                    f.delete()
        except Exception as e:
            Logger.error("AlbumArt::clean_album_cache(): %s" % e)

    def pixbuf_from_tags(self, uri):
        """
            Return cover from tags
            @param uri as str
        """
        pixbuf = None
        # Internal URI are just like sp:
        if uri.find(":/") == -1:
            return
        try:
            discoverer = Discoverer()
            info = discoverer.get_info(uri)
            exist = False
            if info is not None:
                (exist, sample) = info.get_tags().get_sample_index("image", 0)
                if not exist:
                    (exist, sample) = info.get_tags().get_sample_index(
                        "preview-image", 0)
            if exist:
                (exist, mapflags) = sample.get_buffer().map(Gst.MapFlags.READ)
            if exist:
                bytes = GLib.Bytes.new(mapflags.data)
                stream = Gio.MemoryInputStream.new_from_bytes(bytes)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
                stream.close()
        except Exception as e:
            Logger.error("AlbumArt::pixbuf_from_tags(): %s" % e)
        return pixbuf

#######################
# PRIVATE             #
#######################
    def __update_album_uri(self, album):
        """
            Check if album uri exists, update if not
            @param album as Album
        """
        if not album.storage_type & StorageType.COLLECTION:
            return
        d = Gio.File.new_for_uri(album.uri)
        if not d.query_exists():
            if album.tracks:
                track_uri = album.tracks[0].uri
                f = Gio.File.new_for_uri(track_uri)
                p = f.get_parent()
                parent_uri = "" if p is None else p.get_uri()
                album.set_uri(parent_uri)

    def __save_web_album_artwork(self, album, data):
        """
            Save artwork for a web album
            @param album as Album
            @param data as bytes
        """
        store_path = "%s/%s.jpg" % (ALBUMS_WEB_PATH, album.lp_album_id)
        if data is None:
            f = Gio.File.new_for_path(store_path)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            fstream.close()
        else:
            self.save_pixbuf_from_data(store_path, data)
        self.clean_album_cache(album)
        self.album_artwork_update(album.id)

    def __save_ro_album_artwork(self, album, data):
        """
            Save artwork for a read only album
            @param album as Album
            @param data as bytes
        """
        store_path = "%s/%s.jpg" % (ALBUMS_PATH, album.lp_album_id)
        if data is None:
            f = Gio.File.new_for_path(store_path)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            fstream.close()
        else:
            self.save_pixbuf_from_data(store_path, data)
        self.clean_album_cache(album)
        self.album_artwork_update(album.id)

    def __add_album_artwork(self, album, data):
        """
            Save artwork for an album
            @param album as Album
            @param data as bytes
        """
        store_path = "%s/%s.jpg" % (ALBUMS_PATH, album.lp_album_id)
        save_to_tags = App().settings.get_value("save-to-tags")
        # Multiple albums at same path
        uri_count = App().albums.get_uri_count(album.uri)
        art_uri = album.uri + "/" + self.__favorite

        # Save cover to tags
        if save_to_tags:
            helper = TaskHelper()
            helper.run(self.__add_album_artwork_to_tags, album, data)

        # We need to remove favorite if exists
        if uri_count > 1 or save_to_tags:
            f = Gio.File.new_for_uri(art_uri)
            if f.query_exists():
                f.trash()

        # Name file with album information
        if uri_count > 1:
            art_uri = "%s/%s.jpg" % (album.uri, album.lp_album_id)

        if data is None:
            f = Gio.File.new_for_path(store_path)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            fstream.close()
        else:
            self.save_pixbuf_from_data(store_path, data)
        dst = Gio.File.new_for_uri(art_uri)
        src = Gio.File.new_for_path(store_path)
        src.move(dst, Gio.FileCopyFlags.OVERWRITE, None, None)
        self.clean_album_cache(album)
        self.album_artwork_update(album.id)

    def __add_album_artwork_to_tags(self, album, data):
        """
            Save artwork to tags
            @param album as Album
            @param data as bytes
        """
        # https://bugzilla.gnome.org/show_bug.cgi?id=747431
        bytes = GLib.Bytes.new(data)
        stream = Gio.MemoryInputStream.new_from_bytes(bytes)
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                           ArtSize.MPRIS,
                                                           ArtSize.MPRIS,
                                                           True,
                                                           None)
        stream.close()
        pixbuf.savev("%s/lollypop_cover_tags.jpg" % CACHE_PATH,
                     "jpeg", ["quality"], [str(App().settings.get_value(
                                           "cover-quality").get_int32())])
        self.__write_image_to_tags("%s/lollypop_cover_tags.jpg" %
                                   CACHE_PATH, album)

    def __write_image_to_tags(self, path, album):
        """
            Save album at path to album tags
            @param path as str
            @param album as Album
        """
        files = []
        for track in album.tracks:
            App().tracks.set_mtime(track.id, int(time()) + 10)
            f = Gio.File.new_for_uri(track.uri)
            if f.query_exists():
                files.append(f.get_path())
        worked = False
        cover = "%s/lollypop_cover_tags.jpg" % CACHE_PATH
        arguments = [["kid3-cli", "-c", "set picture:'%s' ''" % cover],
                     ["flatpak-spawn", "--host", "kid3-cli",
                      "-c", "set picture:'%s' ''" % cover]]
        for argv in arguments:
            argv += files
            try:
                (pid, stdin, stdout, stderr) = GLib.spawn_async(
                    argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                    GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
                    standard_input=False,
                    standard_output=False,
                    standard_error=False
                )
                GLib.spawn_close_pid(pid)
                worked = True
                break
            except Exception as e:
                Logger.error("AlbumArt::__write_image_to_tags(): %s" % e)
        if worked:
            self.clean_album_cache(album)
            GLib.timeout_add(2000, self.album_artwork_update, album.id)
        else:
            App().notify.send("Lollypop",
                              _("You need to install kid3-cli"))
