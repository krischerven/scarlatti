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

# This is global object initialised at lollypop start
# member init order is important!

from gi.repository import Gio, GLib


LOLLYPOP_DATA_PATH = GLib.get_user_data_dir() + "/lollypop"

App = Gio.Application.get_default

GOOGLE_API_ID = "015987506728554693370:waw3yqru59a"

TAG_EDITORS = ["kid3-qt", "exfalso", "easytag", "picard", "puddletag"]

MARGIN = 15
MARGIN_SMALL = 5


class Repeat:
    NONE = 0
    AUTO = 1
    TRACK = 2
    ALL = 3


class GstPlayFlags:
    GST_PLAY_FLAG_VIDEO = 1 << 0  # We want video output
    GST_PLAY_FLAG_AUDIO = 1 << 1  # We want audio output
    GST_PLAY_FLAG_TEXT = 1 << 3   # We want subtitle output


class ArtBehaviour:
    NONE = 1 << 0
    ROUNDED = 1 << 1
    BLUR = 1 << 2
    BLUR_HARD = 1 << 3
    BLUR_MAX = 1 << 4
    FALLBACK = 1 << 5
    DARKER = 1 << 6
    LIGHTER = 1 << 7
    CROP = 1 << 8
    CROP_SQUARE = 1 << 9
    CACHE = 1 << 10
    NO_CACHE = 1 << 11


class ViewType:
    DEFAULT = 1 << 0
    TWO_COLUMNS = 1 << 1
    DND = 1 << 2
    SEARCH = 1 << 3
    PLAYLISTS = 1 << 4
    POPOVER = 1 << 5
    ALBUM = 1 << 6
    NAVIGATION = 1 << 7
    SMALL = 1 << 8
    MEDIUM = 1 << 9
    SCROLLED = 1 << 10
    FILTERED = 1 << 11
    FULLSCREEN = 1 << 12
    DEVICES = 1 << 13
    NOT_ADAPTIVE = 1 << 14


NetworkAccessACL = {
    "DATA": 1 << 1,
    "LASTFM": 1 << 2,
    "SPOTIFY": 1 << 3,
    "YOUTUBE": 1 << 4,
    "GOOGLE": 1 << 5,
    "STARTPAGE": 1 << 6,
    "WIKIPEDIA": 1 << 7,
    "TUNEIN": 1 << 8,
    "MUSICBRAINZ": 1 << 9,
    "ITUNES": 1 << 10,
    "DEEZER": 1 << 11,
    "WIKIA": 1 << 12,
    "GENIUS": 1 << 13,
    "AUDIODB": 1 << 14
}


class IndicatorType:
    NONE = 1 << 0
    PLAY = 1 << 1
    LOVED = 1 << 2
    SKIP = 1 << 3
    LOADING = 1 << 4


class ArtSize:
    NONE = 0
    SMALL = 33
    MEDIUM = 48  # If changed, adapt width request in AlbumRow
    ARTIST_SMALL = 60
    LARGE = 100
    BANNER = 150
    BIG = 200
    MINIPLAYER = 300
    FULLSCREEN = 400
    ARTIST = 800
    MONSTER = 900
    MAX = 4000


class ScanType:
    EPHEMERAL = 0
    NEW_FILES = 1
    FULL = 2


class SidebarContent:
    DEFAULT = 0
    GENRES = 1
    ARTISTS = 2


class SelectionListMask:
    LIST_ONE = 1 << 1
    LIST_TWO = 1 << 2
    LIST_DEVICE = 1 << 3
    ARTISTS = 1 << 4
    GENRES = 1 << 5
    PLAYLISTS = 1 << 6
    COMPILATIONS = 1 << 7
    ARTISTS_VIEW = 1 << 8


class Shuffle:
    NONE = 0             # No shuffle
    TRACKS = 1           # Shuffle by tracks on genre
    ALBUMS = 2           # Shuffle by albums on genre


class PowerManagement:
    NONE = 0             # Use OS defaults
    IDLE = 1             # Inhibit screensaver
    SUSPEND = 2          # Inhibit suspend
    BOTH = 3             # Inhibit screensaver and suspend


class Sizing:
    MINI = 200
    SMALL = 350
    MEDIUM = 500
    BIG = 700
    MONSTER = 800
    LARGE = 1000


class OrderBy:
    ARTIST = 0
    NAME = 1
    YEAR = 2
    POPULARITY = 3


# Order is important
class Type:
    NONE = -1
    POPULARS = -2
    RANDOMS = -3
    RECENTS = -4
    LOVED = -5
    NEVER = -6
    PLAYLISTS = -7
    RADIOS = -8
    SMART = -9
    SEARCH = -10
    INFO = -11
    YEARS = -12
    ARTISTS = -13
    SETTINGS = -14
    SETTINGS_APPEARANCE = -15
    SETTINGS_BEHAVIOUR = -16
    SETTINGS_COLLECTIONS = -17
    SETTINGS_WEB = -18
    SETTINGS_DEVICES = -19
    EQUALIZER = -20
    GENRES = -21
    # WEB is stored in DB, can't be changed
    WEB = -22
    ALBUM = -23
    ALL = -100
    CURRENT = -101
    DEVICE_ALBUMS = -1000
    DEVICE_PLAYLISTS = -1001
    SEPARATOR = -2000
    COMPILATIONS = -2001


LATIN1_ENCODING = b"\x00"
"""Byte code for latin1"""
UTF_16_ENCODING = b"\x01"
"""Byte code for UTF-16"""
UTF_16BE_ENCODING = b"\x02"
"""Byte code for UTF-16 (big endian)"""
UTF_8_ENCODING = b"\x03"
"""Byte code for UTF-8 (Not supported in ID3 versions < 2.4)"""


SPOTIFY_CLIENT_ID = "0b144843878a46b2b12e0958c342c3ac"
SPOTIFY_SECRET = "265ab8e057684f1b9e69e0c58f4881c1"
AUDIODB_CLIENT_ID = "195003"

STATIC_ALBUM_NAME = {
    Type.POPULARS: "Popular albums",
    Type.RANDOMS: "Random albums",
    Type.LOVED: "Loved albums",
    Type.RECENTS: "Recently added albums",
    Type.NEVER: "Unplayed albums",
    Type.PLAYLISTS: "Playlists",
    Type.RADIOS: "Radios",
    Type.YEARS: "Years",
    Type.ALL: "All albums",
    Type.COMPILATIONS: "Compilations"
}
