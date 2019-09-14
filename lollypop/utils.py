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

from gi.repository import Gio, GLib, Gdk, GdkPixbuf, Pango, Gtk

from math import pi
from gettext import gettext as _
from urllib.parse import urlparse
import unicodedata
import cairo
import time
from functools import wraps

from lollypop.logger import Logger
from lollypop.define import App, Type, NetworkAccessACL
from lollypop.define import StorageType


def cancellable_sleep(seconds, cancellable):
    if not App().debug:
        while seconds > 0:
            time.sleep(0.1)
            seconds -= 0.1
            if cancellable.is_cancelled():
                raise Exception("cancelled")


def seconds_to_string(duration):
    """
        Convert seconds to a pretty string
        @param duration as int
    """
    hours = duration // 3600
    if hours == 0:
        minutes = duration // 60
        seconds = duration % 60
        return "%i:%02i" % (minutes, seconds)
    else:
        seconds = duration % 3600
        minutes = seconds // 60
        seconds %= 60
        return "%i:%02i:%02i" % (hours, minutes, seconds)


def get_human_duration(duration):
    """
        Get human readable duration
        @param duration in seconds
        @return str
    """
    hours = duration // 3600
    minutes = duration // 60
    if hours > 0:
        seconds = duration % 3600
        minutes = seconds // 60
        if minutes > 0:
            return _("%s h  %s m") % (hours, minutes)
        else:
            return _("%s h") % hours
    else:
        return _("%s m") % minutes


def get_round_surface(image, scale_factor, radius):
    """
        Get rounded surface from pixbuf
        @param image as GdkPixbuf.Pixbuf/cairo.Surface
        @return surface as cairo.Surface
        @param scale_factor as int
        @param radius as int
        @warning not thread safe!
    """
    width = image.get_width()
    height = image.get_height()
    is_pixbuf = isinstance(image, GdkPixbuf.Pixbuf)
    if is_pixbuf:
        width = width // scale_factor
        height = height // scale_factor
        radius = radius // scale_factor
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    degrees = pi / 180
    ctx.arc(width - radius, radius, radius, -90 * degrees, 0 * degrees)
    ctx.arc(width - radius, height - radius,
            radius, 0 * degrees, 90 * degrees)
    ctx.arc(radius, height - radius, radius, 90 * degrees, 180 * degrees)
    ctx.arc(radius, radius, radius, 180 * degrees, 270 * degrees)
    ctx.close_path()
    ctx.set_line_width(10)
    if is_pixbuf:
        image = Gdk.cairo_surface_create_from_pixbuf(image, scale_factor, None)
    ctx.set_source_surface(image, 0, 0)
    ctx.clip()
    ctx.paint()
    return surface


def set_cursor_type(widget, name="pointer"):
    """
        Set cursor on widget
        @param widget as Gtk.Widget
        @param name as str
    """
    try:
        window = widget.get_window()
        if window is not None:
            cursor = Gdk.Cursor.new_from_name(Gdk.Display.get_default(),
                                              name)
            window.set_cursor(cursor)
    except:
        pass


def get_default_storage_type():
    """
        Get default collection storage type check
    """
    if get_network_available("YOUTUBE"):
        return StorageType.COLLECTION | StorageType.SAVED
    else:
        return StorageType.COLLECTION


def on_query_tooltip(label, x, y, keyboard, tooltip):
    """
        Show label tooltip if needed
        @param label as Gtk.Label
        @param x as int
        @param y as int
        @param keyboard as bool
        @param tooltip as Gtk.Tooltip
    """
    layout = label.get_layout()
    if layout.is_ellipsized():
        tooltip.set_markup(label.get_label())
        return True


def set_proxy_from_gnome():
    """
        Set proxy settings from GNOME
    """
    try:
        proxy = Gio.Settings.new("org.gnome.system.proxy")
        mode = proxy.get_value("mode").get_string()
        if mode == "manual":
            no_http_proxy = True
            http = Gio.Settings.new("org.gnome.system.proxy.http")
            https = Gio.Settings.new("org.gnome.system.proxy.https")
            h = http.get_value("host").get_string()
            p = http.get_value("port").get_int32()
            hs = https.get_value("host").get_string()
            ps = https.get_value("port").get_int32()
            if h != "" and p != 0:
                no_http_proxy = False
                GLib.setenv("http_proxy", "http://%s:%s" % (h, p), True)
            if hs != "" and ps != 0:
                no_http_proxy = False
                GLib.setenv("https_proxy", "http://%s:%s" % (hs, ps), True)
            if no_http_proxy:
                socks = Gio.Settings.new("org.gnome.system.proxy.socks")
                h = socks.get_value("host").get_string()
                p = socks.get_value("port").get_int32()
                # Set socks proxy
                if h != "" and p != 0:
                    import socket
                    import socks
                    socks.set_default_proxy(socks.SOCKS4, h, p)
                    socket.socket = socks.socksocket
    except Exception as e:
        Logger.error("set_proxy_from_gnome(): %s", e)


def debug(str):
    """
        Print debug
        @param str as str
    """
    if App().debug is True:
        print(str)


def get_network_available(acl_name=""):
    """
        Return True if network available
        @param acl_name as str
        @return bool
    """
    if not App().settings.get_value("network-access"):
        return False
    elif acl_name == "":
        return Gio.NetworkMonitor.get_default().get_network_available()
    else:
        acl = App().settings.get_value("network-access-acl").get_int32()
        if acl & NetworkAccessACL[acl_name]:
            return Gio.NetworkMonitor.get_default().get_network_available()
    return False


def do_shift_selection(listbox, row):
    """
        Do a shift selection on a listbox
    """
    # Get last selected row
    start_row = None
    children = listbox.get_children()
    selected_rows = listbox.get_selected_rows()
    if selected_rows:
        start_row = selected_rows[-1]
    elif children:
        start_row = children[0]
    if start_row is not None:
        start_index = children.index(start_row)
        end_index = children.index(row)
        for i in range(start_index, end_index):
            listbox.select_row(children[i])


def split_list(l, n=1):
    """
        Split list in n parts
        @param l as []
        @param n as int
    """
    length = len(l)
    split = [l[i * length // n: (i + 1) * length // n] for i in range(n)]
    return [l for l in split if l]


def noaccents(string):
    """
        Return string without accents lowered
        @param string as str
        @return str
    """
    nfkd_form = unicodedata.normalize("NFKD", string)
    v = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return v.lower()


def sql_escape(string):
    """
        Escape string for SQL request
        @param string as str
        @param ignore as [str]
    """
    nfkd_form = unicodedata.normalize("NFKD", string)
    v = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return "".join([c for c in v if
                    c.isalpha() or
                    c.isdigit()]).rstrip().lower()


def escape(str, ignore=["_", "-", " ", "."]):
    """
        Escape string
        @param str as str
        @param ignore as [str]
    """
    return "".join([c for c in str if
                    c.isalpha() or
                    c.isdigit() or c in ignore]).rstrip()


def is_unity():
    """
        Return True if desktop is Unity
    """
    return GLib.getenv("XDG_CURRENT_DESKTOP") == "Unity"


def is_gnome():
    """
        Return True if desktop is Gnome
    """
    return GLib.getenv("XDG_CURRENT_DESKTOP") in ["ubuntu:GNOME", "GNOME"]


def is_audio(f):
    """
        Return True if files is audio
        @param f as Gio.File
    """
    audio = ["application/ogg", "application/x-ogg", "application/x-ogm-audio",
             "audio/aac", "audio/mp4", "audio/mpeg", "audio/mpegurl",
             "audio/ogg", "audio/vnd.rn-realaudio", "audio/vorbis",
             "audio/x-flac", "audio/x-mp3", "audio/x-mpeg", "audio/x-mpegurl",
             "audio/x-ms-wma", "audio/x-musepack", "audio/x-oggflac",
             "audio/x-pn-realaudio", "application/x-flac", "audio/x-speex",
             "audio/x-vorbis", "audio/x-vorbis+ogg", "audio/x-wav",
             "x-content/audio-player", "audio/x-aac", "audio/m4a",
             "audio/x-m4a", "audio/mp3", "audio/ac3", "audio/flac",
             "audio/x-opus+ogg", "application/x-extension-mp4", "audio/x-ape",
             "audio/x-pn-aiff", "audio/x-pn-au", "audio/x-pn-wav",
             "audio/x-pn-windows-acm", "application/x-matroska",
             "audio/x-matroska", "audio/x-wavpack", "video/mp4",
             "audio/x-mod", "audio/x-mo3", "audio/x-xm", "audio/x-s3m",
             "audio/x-it", "audio/aiff", "audio/x-aiff"]
    try:
        info = f.query_info("standard::content-type",
                            Gio.FileQueryInfoFlags.NONE)
        if info is not None:
            content_type = info.get_content_type()
            if content_type in audio:
                return True
    except Exception as e:
        Logger.error("is_audio: %s", e)
    return False


def is_pls(f):
    """
        Return True if files is a playlist
        @param f as Gio.File
    """
    try:
        info = f.query_info("standard::content-type",
                            Gio.FileQueryInfoFlags.NONE)
        if info is not None:
            if info.get_content_type() in ["audio/x-mpegurl",
                                           "application/xspf+xml"]:
                return True
    except:
        pass
    return False


def get_mtime(info):
    """
        Return Last modified time of a given file
        @param info as Gio.FileInfo
    """
    # Using time::changed is not reliable making lollypop doing a full
    # scan every two weeks (on my computer)
    # try:
    #    # We do not use time::modified because many tag editors
    #    # just preserve this setting
    #    return int(info.get_attribute_as_string("time::changed"))
    # except:
    #    pass
    return int(info.get_attribute_as_string("time::modified"))


def format_artist_name(name):
    """
        Return formated artist name
        @param name as str
    """
    if not App().settings.get_value("smart-artist-sort"):
        return name
    # Handle language ordering
    # Translators: Add here words that shoud be ignored for artist sort order
    # Translators: Add The the too
    for special in _("The the").split():
        if name.startswith(special + " "):
            strlen = len(special) + 1
            name = name[strlen:] + ", " + special
    return name


def translate_artist_name(name):
    """
        Return translate formated artist name
        @param name as str
    """
    split = name.split("@@@@")
    if len(split) == 2:
        name = split[1] + " " + split[0]
    return name


def tracks_to_albums(tracks):
    """
        Convert tracks list to albums list
    """
    albums = []
    for track in tracks:
        if albums and albums[-1].id == track.album.id:
            albums[-1].append_track(track, False)
        else:
            album = track.album
            album.set_tracks([track], False)
            albums.append(album)
    return albums


def get_page_score(page_title, title, artist, album):
    """
        Calculate web page score
        if page_title looks like (title, artist, album), score is lower
        @return int/None
    """
    page_title = escape(page_title.lower(), [])
    artist = escape(artist.lower(), [])
    album = escape(album.lower(), [])
    title = escape(title.lower(), [])
    # YouTube page title should be at least as long as wanted title
    if len(page_title) < len(title):
        return -1
    # Remove common word for a valid track
    page_title = page_title.replace("official", "")
    page_title = page_title.replace("video", "")
    page_title = page_title.replace("audio", "")
    # Remove artist name
    page_title = page_title.replace(artist, "")
    # Remove album name
    page_title = page_title.replace(album, "")
    # Remove title
    page_title = page_title.replace(title, "")
    return len(page_title)


def is_readonly(uri):
    """
        Check if uri is readonly
    """
    try:
        f = Gio.File.new_for_uri(uri)
        info = f.query_info("access::can-write",
                            Gio.FileQueryInfoFlags.NONE,
                            None)
        return not info.get_attribute_boolean("access::can-write")
    except:
        return True


def create_dir(path):
    """
        Create dir
        @param path as str
    """
    d = Gio.File.new_for_path(path)
    if not d.query_exists():
        try:
            d.make_directory_with_parents()
        except:
            Logger.info("Can't create %s" % path)


def remove_static(ids):
    """
        Remove static ids
        @param ids as [int]
        @return [int]
    """
    # Special case for Type.WEB, only static item present in DB
    return [item for item in ids if item >= 0 or item == Type.WEB]


def get_font_height():
    """
        Get current font height
        @return int
    """
    ctx = App().window.get_pango_context()
    layout = Pango.Layout.new(ctx)
    layout.set_text("A", 1)
    return int(layout.get_pixel_size()[1])


def get_icon_name(object_id):
    """
        Return icon name for id
        @param object_id as int
    """
    icon = ""
    if object_id == Type.SUGGESTIONS:
        icon = "org.gnome.Lollypop-suggestions-symbolic"
    elif object_id == Type.POPULARS:
        icon = "starred-symbolic"
    elif object_id == Type.PLAYLISTS:
        icon = "emblem-documents-symbolic"
    elif object_id == Type.ALL:
        icon = "media-optical-cd-audio-symbolic"
    elif object_id == Type.ARTISTS:
        icon = "avatar-default-symbolic"
    elif object_id == Type.ARTISTS_LIST:
        icon = "org.gnome.Lollypop-artists-list-symbolic"
    elif object_id == Type.COMPILATIONS:
        icon = "system-users-symbolic"
    elif object_id == Type.RECENTS:
        icon = "document-open-recent-symbolic"
    elif object_id == Type.RADIOS:
        icon = "org.gnome.Lollypop-gradio-symbolic"
    elif object_id == Type.RANDOMS:
        icon = "media-playlist-shuffle-symbolic"
    elif object_id == Type.LOVED:
        icon = "emblem-favorite-symbolic"
    elif object_id == Type.NEVER:
        icon = "org.gnome.Lollypop-unplayed-albums-symbolic"
    elif object_id == Type.YEARS:
        icon = "x-office-calendar-symbolic"
    elif object_id == Type.CURRENT:
        icon = "org.gnome.Lollypop-play-queue-symbolic"
    elif object_id == Type.LYRICS:
        icon = "audio-input-microphone-symbolic"
    elif object_id == Type.SEARCH:
        icon = "edit-find-symbolic"
    elif object_id == Type.GENRES:
        icon = "org.gnome.Lollypop-tag-symbolic"
    elif object_id == Type.GENRES_LIST:
        icon = "org.gnome.Lollypop-tag-list-symbolic"
    elif object_id == Type.WEB:
        icon = "goa-panel-symbolic"
    return icon


def update_button(button, style, icon_size, icon_name):
    """
        Update button style
        @param button as Gtk.Button
        @param style as str
        @param icon_size as Gtk.Icon_Size
        @param icon_name as str
    """
    context = button.get_style_context()
    context.remove_class("menu-button-48")
    context.remove_class("menu-button")
    context.add_class(style)
    button.get_image().set_from_icon_name(icon_name, icon_size)


def popup_widget(widget, parent, x=None, y=None):
    """
        Popup menu on widget as x, y
        @param widget as Gtk.Widget
        @param parent as Gtk.Widget
        @param x as int
        @param y as int
        @return Gtk.Popover/None
    """
    def on_closed(widget, hide, popover):
        popover.popdown()

    if App().window.is_adaptive:
        App().window.container.show_menu(widget)
        return None
    else:
        from lollypop.widgets_utils import Popover
        popover = Popover.new()
        popover.add(widget)
        widget.connect("closed", on_closed, popover)
        popover.set_relative_to(parent)
        if x is not None and y is not None:
            rect = Gdk.Rectangle()
            rect.x = x
            rect.y = y
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.popup()
        return popover


def symlink_ok(uri, uris):
    """
        Check if file/dir is a symlink and need to be handled
        @param file_type as Gio.FileType
        @param uri as file/dir URI
        @param uris as base URIS
    """
    for base_uri in uris:
        if uri.startswith(base_uri):
            return False
    return True


def update_track_indexes(listbox, start_index, end_index):
    """
        Update track number from start_index + 1 to end_index
        start_index is a valid track number
        @param listbox as Gtk.ListBox
        @param start_index as int
        @param end_index as int
    """
    if start_index == 0:
        current_number = 0
    else:
        current_number = None
    children = listbox.get_children()
    if end_index == -1:
        end_index = len(children)
    for album_row in children[start_index:end_index]:
        for track in album_row.album.tracks:
            if current_number is None:
                current_number = track.number
                continue
            current_number += 1
            track.set_number(current_number)
        # Update widget for revealed albums
        if album_row.revealed:
            for track_row in album_row.children:
                track_row.update_number_label()


def is_device(mount):
    """
        True if mount is a Lollypop device
        @param mount as Gio.Mount
        @return bool
    """
    if mount.get_volume() is None:
        return False
    uri = mount.get_default_location().get_uri()
    if uri is None:
        return False
    parsed = urlparse(uri)
    if parsed.scheme == "mtp":
        return True
    elif not App().settings.get_value("sync-usb-disks"):
        return False
    drive = mount.get_drive()
    return drive is not None and drive.is_removable()


def profile(f):
    """
        Decorator to get execution time of a function
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()

        ret = f(*args, **kwargs)

        elapsed_time = time.perf_counter() - start_time
        Logger.debug("%s::%s: execution time %d:%f" % (
            f.__module__, f.__name__, elapsed_time / 60, elapsed_time % 60))

        return ret

    return wrapper


def install_youtube_dl():
    try:
        path = GLib.get_user_data_dir() + "/lollypop/python"
        argv = ["pip3", "install", "-t", path, "-U", "youtube-dl"]
        GLib.spawn_sync(None, argv, [], GLib.SpawnFlags.SEARCH_PATH, None)
    except Exception as e:
        Logger.error("install_youtube_dl: %s" % e)


# From eyeD3 start
# eyeD3 is written and maintained by:
# Travis Shirk <travis@pobox.com>
def id3EncodingToString(encoding):
    from lollypop.define import LATIN1_ENCODING, UTF_8_ENCODING
    from lollypop.define import UTF_16_ENCODING, UTF_16BE_ENCODING
    if encoding == LATIN1_ENCODING:
        return "latin_1"
    elif encoding == UTF_8_ENCODING:
        return "utf_8"
    elif encoding == UTF_16_ENCODING:
        return "utf_16"
    elif encoding == UTF_16BE_ENCODING:
        return "utf_16_be"
    else:
        raise ValueError("Encoding unknown: %s" % encoding)


def decodeUnicode(bites, encoding):
    codec = id3EncodingToString(encoding)
    Logger.debug("Unicode encoding: %s" % codec)
    if (codec.startswith("utf_16") and
            len(bites) % 2 != 0 and bites[-1:] == b"\x00"):
        # Catch and fix bad utf16 data, it is everywhere.
        Logger.warning("Fixing utf16 data with extra zero bytes")
        bites = bites[:-1]
    return bites.decode(codec).rstrip("\x00")


def splitUnicode(data, encoding):
    from lollypop.define import LATIN1_ENCODING, UTF_8_ENCODING
    from lollypop.define import UTF_16_ENCODING, UTF_16BE_ENCODING
    try:
        if encoding == LATIN1_ENCODING or encoding == UTF_8_ENCODING:
            (d, t) = data.split(b"\x00", 1)
        elif encoding == UTF_16_ENCODING or encoding == UTF_16BE_ENCODING:
            # Two null bytes split, but since each utf16 char is also two
            # bytes we need to ensure we found a proper boundary.
            (d, t) = data.split(b"\x00\x00", 1)
            if (len(d) % 2) != 0:
                (d, t) = data.split(b"\x00\x00\x00", 1)
                d += b"\x00"
    except ValueError as ex:
        Logger.warning("Invalid 2-tuple ID3 frame data: %s", ex)
        d, t = data, b""
    return (d, t)
# From eyeD3 end
