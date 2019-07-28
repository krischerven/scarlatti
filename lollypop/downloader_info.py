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

from gi.repository import GLib

from gettext import gettext as _
import json
from locale import getdefaultlocale

from lollypop.define import App, AUDIODB_CLIENT_ID
from lollypop.utils import get_network_available
from lollypop.logger import Logger
from lollypop.downloader import Downloader


class Wikipedia:
    """
        Helper for wikipedia search
    """

    __API_SEARCH = "https://%s.wikipedia.org/w/api.php?action=query" +\
        "&list=search&srsearch=%s&format=json"
    __API_INFO = "https://%s.wikipedia.org/w/api.php?action=query" +\
        "&pageids=%s&format=json" +\
        "&prop=extracts&exlimit=max&explaintext&redirects=1"

    def __init__(self):
        """
            Init wikipedia
        """
        self.__locale = getdefaultlocale()[0][0:2]

    def get_content(self, string):
        """
            Get content for string
            @param string as str
            @return str/None
        """
        try:
            (locale, page_id) = self.__search_term(string)
            if page_id is None:
                return None
            uri = self.__API_INFO % (locale, page_id)
            (status, data) = App().task_helper.load_uri_content_sync(uri)
            if status:
                decode = json.loads(data.decode("utf-8"))
                extract = decode["query"]["pages"][str(page_id)]["extract"]
                return extract.encode("utf-8")
        except Exception as e:
            Logger.error("Wikipedia::get_content(): %s", e)
        return None

#######################
# PRIVATE             #
#######################
    def __search_term(self, term):
        """
            Search term on Wikipdia
            @param term as str
            @return pageid as str
        """
        try:
            for locale in [self.__locale, "en"]:
                uri = self.__API_SEARCH % (locale, term)
                (status, data) = App().task_helper.load_uri_content_sync(uri)
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    for item in decode["query"]["search"]:
                        if item["title"].lower() == term.lower():
                            return (locale, item["pageid"])
                        else:
                            for word in [_("band"), _("singer"),
                                         "band", "singer"]:
                                if item["snippet"].lower().find(word) != -1:
                                    return (locale, item["pageid"])
        except Exception as e:
            print("Wikipedia::__search_term(): %s", e)
        return ("", None)


class InfoDownloader(Downloader):
    """
        Download info from the web
    """

    def __init__(self):
        """
            Init info downloader
        """
        Downloader.__init__(self)

    def cache_artist_info(self, artist):
        """
            Cache info for artist
            @param artist as str
        """
        if not get_network_available("DATA"):
            self.emit("artist-info-changed", artist)
            return
        App().task_helper.run(self.__cache_artist_info, artist)

#######################
# PROTECTED           #
#######################
    def _get_audiodb_artist_info(self, artist):
        """
            Get artist info from audiodb
            @param artist as str
            @return info as bytes
        """
        if not get_network_available("AUDIODB"):
            return None
        try:
            artist = GLib.uri_escape_string(artist, None, True)
            uri = "https://theaudiodb.com/api/v1/json/"
            uri += "%s/search.php?s=%s" % (AUDIODB_CLIENT_ID, artist)
            (status, data) = App().task_helper.load_uri_content_sync(uri, None)
            if status:
                decode = json.loads(data.decode("utf-8"))
                language = getdefaultlocale()[0][-2:]
                for item in decode["artists"]:
                    for key in ["strBiography%s" % language,
                                "strBiographyEN"]:
                        info = item[key]
                        if info is not None:
                            return info.encode("utf-8")
        except Exception as e:
            Logger.error("InfoDownloader::_get_audiodb_artist_info: %s, %s" %
                         (e, artist))
        return None

    def _get_lastfm_artist_info(self, artist):
        """
            Get artist info from audiodb
            @param artist as str
            @return info as bytes
        """
        info = None
        try:
            if App().lastfm is not None and get_network_available("LASTFM"):
                info = App().lastfm.get_artist_bio(artist)
        except Exception as e:
            Logger.error("InfoDownloader::_get_lastfm_artist_info(): %s" % e)
        return info

#######################
# PRIVATE             #
#######################
    def __cache_artist_info(self, artist):
        """
            Cache artist information
            @param artist as str
        """
        content = None
        try:
            if get_network_available("WIKIPEDIA"):
                wikipedia = Wikipedia()
                content = wikipedia.get_content(artist)
            if content is None:
                for (api, a_helper, ar_helper, helper) in self._WEBSERVICES:
                    if helper is None:
                        continue
                    try:
                        method = getattr(self, helper)
                        content = method(artist)
                        if content is not None:
                            break
                    except Exception as e:
                        Logger.error(
                            "InfoDownloader::__cache_artists_artwork(): %s"
                            % e)
            self.save_artist_information(artist, content)
        except Exception as e:
            Logger.info("InfoDownloader::__cache_artist_info(): %s" % e)
        GLib.idle_add(self.emit, "artist-info-changed", artist)
