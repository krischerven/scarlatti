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

from gi.repository import GObject, Gio, GLib, GdkPixbuf

from PIL import Image, ImageFilter

from lollypop.define import ArtSize, App, TAG_EDITORS, ArtBehaviour
from lollypop.logger import Logger


class BaseArt(GObject.GObject):
    """
        Base art manager
    """
    _CACHE_PATH = GLib.get_user_cache_dir() + "/lollypop"
    # Fallback when album dir is readonly
    _STORE_PATH = GLib.get_user_data_dir() + "/lollypop/store"
    # Store for Web
    _WEB_PATH = GLib.get_user_data_dir() + "/lollypop/web_store"
    __gsignals__ = {
        "album-artwork-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "artist-artwork-changed": (GObject.SignalFlags.RUN_FIRST,
                                   None, (str,)),
        "radio-artwork-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "uri-artwork-found": (GObject.SignalFlags.RUN_FIRST, None,
                              (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self):
        """
            Init base art
        """
        GObject.GObject.__init__(self)
        self.__kid3_available = False
        self.__tag_editor = App().settings.get_value("tag-editor").get_string()
        self.__kid3_cli_search()
        self.__tag_editor_search()

    def load_behaviour(self, pixbuf, cache_path, width, height, behaviour):
        """
            Load behaviour on pixbuf
            @param cache_path as str
            @param width as int
            @param height as int
            @param behaviour as ArtBehaviour
        """
        # Crop image as square
        if behaviour & ArtBehaviour.CROP_SQUARE:
            pixbuf = self._crop_pixbuf_square(pixbuf)
            pixbuf = pixbuf.scale_simple(width, height,
                                         GdkPixbuf.InterpType.BILINEAR)
        # Crop image keeping ratio
        if behaviour & ArtBehaviour.CROP:
            pixbuf = self._crop_pixbuf(pixbuf, width, height)

        # Handle blur
        if behaviour & ArtBehaviour.BLUR:
            pixbuf = pixbuf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.NEAREST)
            pixbuf = self._get_blur(pixbuf, 25)
        elif behaviour & ArtBehaviour.BLUR_HARD:
            pixbuf = pixbuf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.NEAREST)
            pixbuf = self._get_blur(pixbuf, 50)
        elif behaviour & ArtBehaviour.BLUR_MAX:
            pixbuf = pixbuf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.NEAREST)
            pixbuf = self._get_blur(pixbuf, 100)
        elif behaviour & ArtBehaviour.CROP:
            pixbuf = pixbuf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.HYPER)
            pass
        else:
            pixbuf = pixbuf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.BILINEAR)
        if behaviour & ArtBehaviour.CACHE and cache_path is not None:
            if cache_path.endswith(".jpg"):
                pixbuf.savev(cache_path, "jpeg", ["quality"],
                             [str(App().settings.get_value(
                                 "cover-quality").get_int32())])
            else:
                pixbuf.savev(cache_path, "png", [None], [None])
        return pixbuf

    def update_art_size(self):
        """
            Update value with some check
        """
        value = App().settings.get_value("cover-size").get_int32()
        # Check value as user can enter bad value via dconf
        if value < ArtSize.SMALL or value > ArtSize.MAX:
            value = 200
        ArtSize.BIG = value
        ArtSize.BANNER = int(ArtSize.BIG * 150 / 200)
        ArtSize.ARTIST_SMALL = int(ArtSize.BIG * 60 / 200)

    def clean_store(self, filename):
        """
            @param filename as str
        """
        try:
            filepath = self._STORE_PATH + "/" + filename + ".jpg"
            f = Gio.File.new_for_path(filepath)
            if f.query_exists():
                f.delete()
        except Exception as e:
            Logger.error("Art::clean_store(): %s" % e)

    @property
    def kid3_available(self):
        """
            True if kid3 is available
            @return bool
        """
        return self.__kid3_available

    @property
    def tag_editor(self):
        """
            Get tag editor
            @return bool
        """
        return self.__tag_editor

#######################
# PROTECTED           #
#######################
    def _save_pixbuf_from_data(self, path, data):
        """
            Save a pixbuf at path from data
            @param path as str
            @param data as bytes
        """
        # Create an empty file
        if data is None:
            f = Gio.File.new_for_path(path)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION,
                                None)
            fstream.close()
        else:
            bytes = GLib.Bytes(data)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
            stream.close()
            pixbuf.savev(path, "jpeg", ["quality"],
                         [str(App().settings.get_value(
                             "cover-quality").get_int32())])

    def _crop_pixbuf(self, pixbuf, wanted_width, wanted_height):
        """
            Crop pixbuf
            @param pixbuf as GdkPixbuf.Pixbuf
            @param wanted_width as int
            @param wanted height as int
            @return GdkPixbuf.Pixbuf
        """
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        aspect = width / height
        wanted_aspect = wanted_width / wanted_height
        if aspect > wanted_aspect:
            new_width = height * wanted_aspect
            offset = (width - new_width)
            return pixbuf.new_subpixbuf(offset / 2,
                                        0,
                                        width - offset,
                                        height)
        else:
            new_height = width / wanted_aspect
            offset = (height - new_height)
            return pixbuf.new_subpixbuf(0,
                                        offset / 2,
                                        width,
                                        height - offset)

    def _crop_pixbuf_square(self, pixbuf):
        """
            Crop pixbuf as square
            @param pixbuf as GdkPixbuf.Pixbuf
            @return GdkPixbuf.Pixbuf
        """
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        if width == height:
            return pixbuf
        elif width > height:
            diff = (width - height)
            return pixbuf.new_subpixbuf(diff / 2,
                                        0,
                                        width - diff,
                                        height)
        else:
            diff = (height - width)
            return pixbuf.new_subpixbuf(0,
                                        diff / 2,
                                        width,
                                        height - diff)

    def _get_blur(self, pixbuf, gaussian):
        """
            Blur surface using PIL
            @param pixbuf as GdkPixbuf.Pixbuf
            @param gaussian as int
            @return GdkPixbuf.Pixbuf
        """
        if pixbuf is None:
            return None
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        data = pixbuf.get_pixels()
        stride = pixbuf.get_rowstride()
        has_alpha = pixbuf.get_has_alpha()
        if has_alpha:
            mode = "RGBA"
            dst_row_stride = width * 4
        else:
            mode = "RGB"
            dst_row_stride = width * 3
        tmp = Image.frombytes(mode, (width, height),
                              data, "raw", mode, stride)
        tmp = tmp.filter(ImageFilter.GaussianBlur(gaussian))
        bytes = GLib.Bytes.new(tmp.tobytes())
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(bytes,
                                                 GdkPixbuf.Colorspace.RGB,
                                                 has_alpha,
                                                 8,
                                                 width,
                                                 height,
                                                 dst_row_stride)
        return pixbuf

#######################
# PRIVATE             #
#######################
    def __tag_editor_search(self, editors=TAG_EDITORS):
        """
            Search for tag editor
        """
        # Search for available tag editors
        if not self.__tag_editor and editors:
            editor = editors.pop(0)
            if GLib.find_program_in_path("flatpak-spawn") is not None:
                argv = ["flatpak-spawn", "--host",
                        "sh", "-c", 'command -v %s' % editor]
            elif GLib.find_program_in_path(editor) is not None:
                self.__tag_editor = editor
                return
            try:
                (pid, stdin, stdout, stderr) = GLib.spawn_async(
                    argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                    GLib.SpawnFlags.STDOUT_TO_DEV_NULL |
                    GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                    standard_input=False,
                    standard_output=False,
                    standard_error=False
                )
                GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid,
                                     self.__on_tag_editor_result,
                                     editor, editors)
            except:
                self.__on_tag_editor_result(None, 1, editor, editors)

    def __kid3_cli_search(self):
        """
            Search for kid3-cli
        """
        if GLib.find_program_in_path("flatpak-spawn") is not None:
            argv = ["flatpak-spawn", "--host",
                    "sh", "-c", 'command -v kid3-cli']
        elif GLib.find_program_in_path("kid3-cli") is not None:
            self.__kid3_available = True
            return
        try:
            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                GLib.SpawnFlags.STDOUT_TO_DEV_NULL |
                GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                standard_input=False,
                standard_output=False,
                standard_error=False
            )
            GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid,
                                 self.__on_kid3_result)
        except:
            self.__on_kid3_result(None, 1)

    def __on_tag_editor_result(self, pid, status, editor, editors):
        """
            Set editor
            @param pid as int
            @param status as bool
            @param editor as str
            @param editors as [str]
        """
        if pid is not None:
            GLib.spawn_close_pid(pid)
        if status == 0:
            self.__tag_editor = editor
        else:
            self.__tag_editor_search(editors)

    def __on_kid3_result(self, pid, status):
        """
            Set state
            @param pid as int
            @param status as bool
        """
        if pid is not None:
            GLib.spawn_close_pid(pid)
        self.__kid3_available = status == 0
