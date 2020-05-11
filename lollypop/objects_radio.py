# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2015 Jean-Philippe Braun <eon@patapon.info>
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

from gettext import gettext as _
from hashlib import md5

from lollypop.define import App, Type, StorageType
from lollypop.objects import Base


class RadioAlbum:
    """
        Fake album
    """
    def __init__(self, radio_id):
        """
            Init album
            @param radio_id as int
        """
        self.id = radio_id
        self.name = App().radios.get_name(radio_id)
        self.storage_type = StorageType.COLLECTION
        self.artists = [_("Radio")]
        self.artist_ids = [Type.RADIOS]
        self.year = None
        self.timestamp = self.duration = self.popularity = self.mtime = 0
        self.uri = ""
        self.track_count = 1
        self.mb_album_id = None
        self.loved = False
        self.synced = False
        self.tracks = []
        self.track_ids = []
        self.lp_album_id = md5(self.name.encode("utf-8")).hexdigest()


class Radio(Base):
    """
        Represent a radio
    """
    DEFAULTS = {"name": "",
                "popularity": 0,
                "uri": ""}

    def __init__(self, radio_id):
        """
            Init track
            @param radio_id as int
        """
        Base.__init__(self, App().radios)
        self.id = self.album_id = radio_id
        self.storage_type = StorageType.COLLECTION
        self.album = RadioAlbum(radio_id)
        self.artists = self.genres = self.album_artists = [_("Radio")]
        self.path = self.discname = ""
        self.artist_ids = self.genre_ids = [Type.RADIOS]
        self.album_name = self.album.name
        self.year = None
        self.duration = self.number = self.discnumber =\
            self.timestamp = self.mtime = self.mb_track_id = self.position = 0
        self.loved = self.last = False
        self.mb_artist_ids = []
        self.is_web = self.is_http = True
        self.lp_track_id = md5(self.album_name.encode("utf-8")).hexdigest()

    def set_name(self, name):
        """
            Set uri
            @param uri as str
        """
        self.name = name

    def set_uri(self, uri):
        """
            Set uri
            @param uri as str
        """
        self.uri = uri

    @property
    def title(self):
        return self.name
