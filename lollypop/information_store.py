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

from gi.repository import Gio, GObject

from hashlib import md5

from lollypop.define import ARTISTS_PATH
from lollypop.logger import Logger
from lollypop.downloader_info import InfoDownloader


class InformationStore(GObject.Object, InfoDownloader):
    """
        Generic class to cache information
    """

    __gsignals__ = {
        "artist-info-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        """
            Init store
        """
        GObject.Object.__init__(self)
        InfoDownloader.__init__(self)

    def get_artist_information(self, artist):
        """
            Get artist information
            @param artist as str
            @return content as bytes
        """
        encoded = md5(artist.encode("utf-8")).hexdigest()
        filepath = "%s/%s.txt" % (ARTISTS_PATH, encoded)
        content = None
        f = Gio.File.new_for_path(filepath)
        if f.query_exists():
            (status, content, tag) = f.load_contents()
        return content

    def save_artist_information(self, artist, content):
        """
            Save artist information
            @param artist as str
            @param content as bytes
        """
        try:
            if content is not None:
                encoded = md5(artist.encode("utf-8")).hexdigest()
                filepath = "%s/%s.txt" % (ARTISTS_PATH, encoded)
                f = Gio.File.new_for_path(filepath)
                fstream = f.replace(None, False,
                                    Gio.FileCreateFlags.REPLACE_DESTINATION,
                                    None)
                if fstream is not None:
                    fstream.write(content, None)
                    fstream.close()
        except Exception as e:
            Logger.error("InformationStore::save_artist_information(): %s", e)
