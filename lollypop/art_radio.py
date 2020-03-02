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

import re

from lollypop.helper_task import TaskHelper
from lollypop.logger import Logger
from lollypop.define import ArtBehaviour, CACHE_PATH
from lollypop.utils import escape, emit_signal
from lollypop.utils_file import create_dir


class RadioArt:
    """
        Manage radio artwork
    """
    _RADIOS_PATH = GLib.get_user_data_dir() + "/lollypop/radios"

    def __init__(self):
        """
            Init radio art
            Should be inherited by a BaseArt
        """
        create_dir(self._RADIOS_PATH)

    def get_radio_cache_path(self, name, width, height):
        """
            get cover cache path for radio
            @param name as str
            @param width as int
            @param height as int
            @return cover path as string or None if no cover
        """
        filename = ""
        try:
            filename = self.__get_radio_cache_name(name)
            cache_path_png = "%s/%s_%s_%s.png" % (CACHE_PATH,
                                                  filename,
                                                  width,
                                                  height)
            f = Gio.File.new_for_path(cache_path_png)
            if f.query_exists():
                return cache_path_png
            else:
                self.get_radio_artwork(name, width, height, 1)
                if f.query_exists():
                    return cache_path_png
        except Exception as e:
            Logger.error("RadioArt::get_radio_cache_path(): %s, %s" %
                         (e, ascii(filename)))
            return None

    def get_radio_artwork(self, name, width, height, scale_factor,
                          behaviour=ArtBehaviour.CACHE |
                          ArtBehaviour.CROP_SQUARE):
        """
            Return a cairo surface for radio name
            @param name as string
            @param width as int
            @param height as int
            @param scale_factor as int
            @param behaviour as ArtBehaviour
            @return GdkPixbuf.Pixbuf
        """
        width *= scale_factor
        height *= scale_factor
        filename = self.__get_radio_cache_name(name)
        cache_path_png = "%s/%s_%s_%s.png" % (CACHE_PATH, filename,
                                              width, height)
        pixbuf = None
        try:
            # Look in cache
            f = Gio.File.new_for_path(cache_path_png)
            if not behaviour & ArtBehaviour.NO_CACHE and f.query_exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(cache_path_png,
                                                                width,
                                                                height)
            else:
                filepath = self.__get_radio_art_path(name)
                f = Gio.File.new_for_path(filepath)
                if f.query_exists():
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(filepath)
                    pixbuf = self.load_behaviour(pixbuf, cache_path_png,
                                                 width, height, behaviour)
        except Exception as e:
            Logger.error("RadioArt::get_radio_artwork(): %s" % e)
        return pixbuf

    def cache_radio_uri(self, uri, name):
        """
            Copy uri to cache at size
            @param uri as str
            @param name as str
        """
        helper = TaskHelper()
        helper.load_uri_content(uri,
                                None,
                                self.__on_uri_content,
                                name)

    def rename_radio(self, old_name, new_name):
        """
            Rename artwork
            @param old_name as str
            @param new_name as str
        """
        old = self.__get_radio_art_path(old_name)
        new = self.__get_radio_art_path(new_name)
        try:
            src = Gio.File.new_for_path(old)
            dst = Gio.File.new_for_path(new)
            if src.query_exists():
                src.move(dst, Gio.FileCopyFlags.OVERWRITE, None, None)
        except Exception as e:
            Logger.error("RadioArt::rename_radio(): %s" % e)

    def add_radio_artwork(self, name, data):
        """
            Add radio artwork to store
            @param name as str
            @param data as bytes
            @thread safe
        """
        self.uncache_radio_artwork(name)
        filepath = "%s/%s.png" % (self._RADIOS_PATH, escape(name))
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
            pixbuf.savev(filepath, "png", [None], [None])
        emit_signal(self, "radio-artwork-changed", name)

    def uncache_radio_artwork(self, name):
        """
            Remove radio artwork from cache
            @param name as string
        """
        cache_name = self.__get_radio_cache_name(name)
        try:
            f = Gio.File.new_for_path(CACHE_PATH)
            infos = f.enumerate_children(
                "standard::name",
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None)
            for info in infos:
                f = infos.get_child(info)
                basename = f.get_basename()
                if re.search(r"%s_.*\.png" % re.escape(cache_name), basename):
                    f.delete()
            infos.close(None)
        except Exception as e:
            Logger.error("RadioArt::clean_radio_cache(): %s, %s" %
                         (e, cache_name))

#######################
# PRIVATE             #
#######################
    def __get_radio_art_path(self, name):
        """
            Get radio artwork path
            @param name as str
            @return filepath as str
        """
        return "%s/%s.png" % (self._RADIOS_PATH, escape(name))

    def __get_radio_cache_name(self, name):
        """
            Get a uniq string for radio
            @param album_id as int
            @param sql as sqlite cursor
        """
        return "@@" + escape(name) + "@@radio@@"

    def __on_uri_content(self, uri, status, content, name):
        """
            Save image
            @param uri as str
            @param status as bool
            @param content as bytes  # The image
            @param name as str
        """
        if status:
            cache_path_png = self.__get_radio_art_path(name)
            bytes = GLib.Bytes.new(content)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
            stream.close()
            pixbuf.savev(cache_path_png, "png", [None], [None])
            del pixbuf
            emit_signal(self, "radio-artwork-changed", name)
