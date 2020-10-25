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

from gi.repository import GLib

import json

from lollypop.define import App, GOOGLE_API_ID, Type, AUDIODB_CLIENT_ID
from lollypop.define import FANARTTV_ID
from lollypop.define import StorageType
from lollypop.utils import get_network_available, noaccents, emit_signal
from lollypop.logger import Logger
from lollypop.objects_album import Album


class DownloaderArt:
    """
        Download art from the web
    """

    def __init__(self):
        """
            Init art downloader
        """
        self.__album_methods = {
            "AudioDB": self._get_audiodb_album_artwork_uri,
            "FanartTV": self._get_fanarttv_album_artwork_uri,
            "Spotify": self._get_spotify_album_artwork_uri,
            "Itunes": self._get_itunes_album_artwork_uri,
            "Deezer": self._get_deezer_album_artwork_uri,
            "Last.fm": self._get_lastfm_album_artwork_uri
        }
        self.__artist_methods = {
            "AudioDB": self._get_audiodb_artist_artwork_uri,
            "FanartTV": self._get_fanarttv_artist_artwork_uri,
            "Spotify": self._get_spotify_artist_artwork_uri,
            "Deezer": self._get_deezer_artist_artwork_uri
        }
        self.__albums_queue = []
        self.__artists_queue = []
        self.__in_albums_download = False
        self.__in_artists_download = False

    def add_artist_artwork_from_uri(self, artist, uri,
                                    cancellable, storage_type):
        """
            Add artist artwork
            @param artist as str
            @param uri as str
            @param cancellable as Gio.Cancellable
            @param storage_type as int
        """
        def on_uri_content(uri, status, data):
            if status:
                App().art.add_artist_artwork(artist, data, storage_type)
        if uri:
            App().task_helper.load_uri_content(uri,
                                               cancellable,
                                               on_uri_content)

    def search_album_artworks(self, artist, album, cancellable):
        """
            Search album artworks
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @thread safe
        """
        results = []
        for api in self.__album_methods.keys():
            uris = self.__album_methods[api](artist, album, cancellable)
            for uri in uris:
                results.append((uri, api))
        emit_signal(self, "uri-artwork-found", results)

    def search_artist_artwork(self, artist, cancellable):
        """
            Search artist artwork
            @param album as str
            @param cancellable as Gio.Cancellable
            @thread safe
        """
        results = []
        for api in self.__artist_methods.keys():
            uris = self.__artist_methods[api](artist, cancellable)
            for uri in uris:
                results.append((uri, api))
        emit_signal(self, "uri-artwork-found", results)

    def cache_album_artwork(self, album_id):
        """
            Download album artwork
            @param album_id as int
        """
        if not get_network_available("DATA"):
            return
        self.__albums_queue.append(album_id)
        if not self.__in_albums_download:
            App().task_helper.run(self.__cache_albums_artwork)

    def cache_artist_artwork(self, artist):
        """
            Cache artist artwork
            @param artist as str
        """
        if not get_network_available("DATA"):
            return
        self.__artists_queue.append(artist)
        if not self.__in_artists_download:
            App().task_helper.run(self.__cache_artists_artwork)

    def search_artwork_from_google(self, search, cancellable):
        """
            Get google uri for search
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        if not get_network_available("GOOGLE"):
            emit_signal(self, "uri-artwork-found", None)
            return
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        uri = "https://www.googleapis.com/" +\
              "customsearch/v1?key=%s&cx=%s" % (key, GOOGLE_API_ID) +\
              "&q=%s&searchType=image" % GLib.uri_escape_string(search,
                                                                "",
                                                                False)
        App().task_helper.load_uri_content(uri,
                                           cancellable,
                                           self.__on_load_google_content)

    def search_artwork_from_startpage(self, search, cancellable):
        """
            Get google uri for search
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        if not get_network_available("STARTPAGE"):
            emit_signal(self, "uri-artwork-found", None)
            return
        uri = "https://www.startpage.com/do/search?flimgsize=isz%3Al"
        uri += "&image-size-select=&flimgexwidth=&flimgexheight=&abp=-1"
        uri += "&cat=pics&query=%s" % GLib.uri_escape_string(search, "", False)
        App().task_helper.load_uri_content(uri,
                                           cancellable,
                                           self.__on_load_startpage_content)

#######################
# PROTECTED           #
#######################
    def _get_audiodb_artist_artwork_uri(self, artist, cancellable=None):
        """
            Get artist artwork using AutdioDB
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @thread safe
        """
        if not get_network_available("AUDIODB"):
            return []
        try:
            artist = GLib.uri_escape_string(artist, None, True)
            uri = "https://theaudiodb.com/api/v1/json/"
            uri += "%s/search.php?s=%s" % (AUDIODB_CLIENT_ID, artist)
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                uri = None
                for item in decode["artists"]:
                    for key in ["strArtistFanart", "strArtistThumb"]:
                        uri = item[key]
                        if uri is not None:
                            return [uri]
        except Exception as e:
            Logger.warning("%s %s", e, artist)
            Logger.warning(
                "DownloaderArt::_get_audiodb_artist_artwork_uri: %s", data)
        return []

    def _get_deezer_artist_artwork_uri(self, artist, cancellable=None):
        """
            Get artist artwork using Deezer
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("DEEZER"):
            return []
        try:
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.deezer.com/search/artist/?" +\
                  "q=%s&output=json&index=0&limit=1" % artist_formated
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                uri = None
                decode = json.loads(data.decode("utf-8"))
                uri = decode["data"][0]["picture_xl"]
                return [uri]
        except Exception as e:
            Logger.warning("%s %s", e, artist)
            Logger.warning(
                "DownloaderArt::_get_deezer_artist_artwork_uri(): %s", data)
        return []

    def _get_fanarttv_artist_artwork_uri(self, artist, cancellable=None):
        """
            Get artist artwork using FanartTV
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @thread safe
        """
        if not get_network_available("FANARTTV"):
            return []
        uris = []
        try:
            mbid = self.__get_musicbrainz_mbid("artist", artist, cancellable)
            if mbid is None:
                return []
            uri = "http://webservice.fanart.tv/v3/music/%s?api_key=%s"
            (status, data) = App().task_helper.load_uri_content_sync(
                uri % (mbid, FANARTTV_ID), cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artistbackground"]:
                    uris.append(item["url"])
        except Exception as e:
            Logger.warning("%s %s", e, artist)
            Logger.warning(
                "DownloaderArt::_get_fanarttv_artist_artwork_uri: %s", data)
        return uris

    def _get_spotify_artist_artwork_uri(self, artist, cancellable=None):
        """
            Get artist artwork using Spotify
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("SPOTIFY"):
            return []
        try:
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.spotify.com/v1/search?q=%s" % artist_formated +\
                  "&type=artist"
            token = App().ws_director.token_ws.get_token("SPOTIFY",
                                                         cancellable)
            bearer = "Bearer %s" % token
            headers = [("Authorization", bearer)]
            (status,
             data) = App().task_helper.load_uri_content_sync_with_headers(
                    uri, headers, cancellable)
            if status:
                uri = None
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    if noaccents(item["name"].lower()) ==\
                            noaccents(artist.lower()):
                        uri = item["images"][0]["url"]
                        return [uri]
        except Exception as e:
            Logger.warning("%s %s", e, artist)
            Logger.warning(
                "DownloaderArt::_get_spotify_artist_artwork_uri(): %s", data)
        return []

    def _get_deezer_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork using Deezer
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("DEEZER"):
            return []
        try:
            album_formated = GLib.uri_escape_string(album, None, True)
            uri = "https://api.deezer.com/search/album/?" +\
                  "q=%s&output=json" % album_formated
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                uri = None
                for item in decode["data"]:
                    if noaccents(item["artist"]["name"].lower()) ==\
                            noaccents(artist.lower()):
                        uri = item["cover_xl"]
                        return [uri]
        except Exception as e:
            Logger.warning("%s %s %s", e, artist, album)
            Logger.warning("DownloaderArt::__get_deezer_album_artwork_uri: %s",
                           data)
        return []

    def _get_fanarttv_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork using FanartTV
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @thread safe
        """
        if not get_network_available("FANARTTV"):
            return []
        uris = []
        try:
            search = "%s %s" % (artist, album)
            mbid = self.__get_musicbrainz_mbid("album", search, cancellable)
            if mbid is None:
                return []
            uri = "http://webservice.fanart.tv/v3/music/albums/%s?api_key=%s"
            (status, data) = App().task_helper.load_uri_content_sync(
                uri % (mbid, FANARTTV_ID), cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for cover in decode["albums"][mbid]["albumcover"]:
                    uris.append(cover["url"])
        except Exception as e:
            Logger.warning("%s %s %s", e, artist, album)
            Logger.warning(
                "DownloaderArt::_get_fanarttv_album_artwork_uri: %s", data)
        return uris

    def _get_spotify_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork using Spotify
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("SPOTIFY"):
            return []
        artists_spotify_ids = []
        try:
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.spotify.com/v1/search?q=%s" % artist_formated +\
                  "&type=artist"
            token = App().ws_director.token_ws.get_token("SPOTIFY",
                                                         cancellable)
            bearer = "Bearer %s" % token
            headers = [("Authorization", bearer)]
            (status,
             data) = App().task_helper.load_uri_content_sync_with_headers(
                    uri, headers, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    artists_spotify_ids.append(item["id"])

            for artist_spotify_id in artists_spotify_ids:
                uri = "https://api.spotify.com/v1/artists/" +\
                      "%s/albums" % artist_spotify_id
                (status,
                 data) = App().task_helper.load_uri_content_sync_with_headers(
                    uri, headers, cancellable)
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    uri = None
                    for item in decode["items"]:
                        if noaccents(item["name"].lower()) ==\
                                noaccents(album.lower()):
                            return [item["images"][0]["url"]]
        except Exception as e:
            Logger.warning("%s %s %s", e, artist, album)
            Logger.warning(
                "DownloaderArt::_get_album_art_spotify_uri: %s", data)
        return []

    def _get_itunes_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork using Itunes
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("ITUNES"):
            return []
        try:
            album_formated = GLib.uri_escape_string(
                album, None, True).replace(" ", "+")
            uri = "https://itunes.apple.com/search" +\
                  "?entity=album&term=%s" % album_formated
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["results"]:
                    if noaccents(item["artistName"].lower()) ==\
                            noaccents(artist.lower()):
                        uri = item["artworkUrl60"].replace("60x60",
                                                           "1024x1024")
                        return [uri]
        except Exception as e:
            Logger.warning("%s %s %s", e, artist, album)
            Logger.warning(
                "DownloaderArt::_get_album_art_itunes_uri: %s", data)
        return []

    def _get_audiodb_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork using AudioDB
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @thread safe
        """
        if not get_network_available("AUDIODB"):
            return []
        try:
            album = GLib.uri_escape_string(album, None, True)
            artist = GLib.uri_escape_string(artist, None, True)
            uri = "https://theaudiodb.com/api/v1/json/"
            uri += "%s/searchalbum.php?s=%s&a=%s" % (AUDIODB_CLIENT_ID,
                                                     artist,
                                                     album)
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                if decode["album"]:
                    for item in decode["album"]:
                        uri = item["strAlbumThumb"]
                        return [uri]
        except Exception as e:
            Logger.warning("%s %s %s", e, artist, album)
            Logger.warning(
                "DownloaderArt::_get_audiodb_album_artwork_uri: %s", data)
        return []

    def _get_lastfm_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork using Last.fm
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return [str]
            @tread safe
        """
        if not get_network_available("LASTFM"):
            return []
        try:
            from lollypop.helper_web_lastfm import LastFMWebHelper
            helper = LastFMWebHelper()
            payload = helper.get_album_payload(album, artist, cancellable)
            artwork_uri = payload["image"][-1]["#text"]
            return [artwork_uri]
        except Exception as e:
            Logger.warning("%s %s %s", e, artist, album)
            Logger.warning(
                "DownloaderArt::_get_album_art_lastfm_uri: %s", payload)
        return []

#######################
# PRIVATE             #
#######################
    def __get_musicbrainz_mbid(self, mbid_type, string, cancellable):
        """
            Get musicbrainz mbid for type and string
            @param mbid_type as str ("artist" or "album")
            @param string as str
            @param cancellable as Gio.Cancellable
        """
        try:
            if mbid_type == "artist":
                uri = "http://musicbrainz.org/ws/2/artist/" +\
                      "?query=%s&fmt=json"
            else:
                uri = "http://musicbrainz.org/ws/2/release-group/" +\
                      "?query=%s&fmt=json"
            string = GLib.uri_escape_string(string, None, True)
            (status, data) = App().task_helper.load_uri_content_sync(
                                                          uri % string,
                                                          cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                if mbid_type == "artist":
                    for item in decode["artists"]:
                        return item["id"]
                else:
                    mbid = None
                    # Get album id or EP id if missing
                    for item in decode["release-groups"]:
                        if item["primary-type"] == "Album":
                            mbid = item["id"]
                            break
                        elif item["primary-type"] == "EP" and mbid is None:
                            mbid = item["id"]
                return mbid
        except Exception as e:
            Logger.warning("%s %s", e, string)
            Logger.warning("DownloaderArt::__get_musicbrainz_mbid: %s", data)
        return None

    def __cache_artists_artwork(self):
        """
            Cache artwork for all artists
        """
        self.__in_artists_download = True
        try:
            while self.__artists_queue:
                artist = self.__artists_queue.pop()
                found = False
                for api in self.__artist_methods.keys():
                    result = self.__artist_methods[api](artist)
                    for uri in result:
                        (status,
                         data) = App().task_helper.load_uri_content_sync(
                            uri, None)
                        if status:
                            found = True
                            App().art.add_artist_artwork(
                                artist, data, StorageType.COLLECTION)
                            break
                    # Found, do not search in another helper
                    if found:
                        break
                # Not found, save empty artwork
                if not found:
                    App().art.add_artist_artwork(artist, None,
                                                 StorageType.COLLECTION)
        except Exception as e:
            Logger.error("DownloaderArt::__cache_artists_artwork(): %s" % e)
        self.__in_artists_download = False

    def __cache_albums_artwork(self):
        """
            Cache albums artwork (from queue)
            @thread safe
        """
        self.__in_albums_download = True
        try:
            while self.__albums_queue:
                album_id = self.__albums_queue.pop()
                album = App().albums.get_name(album_id)
                artist_ids = App().albums.get_artist_ids(album_id)
                is_compilation = artist_ids and\
                    artist_ids[0] == Type.COMPILATIONS
                if is_compilation:
                    artist = ""
                else:
                    artist = ", ".join(App().albums.get_artists(album_id))
                found = False
                for api in self.__album_methods.keys():
                    result = self.__album_methods[api](artist, album)
                    for uri in result:
                        (status,
                         data) = App().task_helper.load_uri_content_sync(uri,
                                                                         None)
                        if status:
                            found = True
                            App().art.save_album_artwork(Album(album_id), data)
                            break
                    # Found, do not search in another helper
                    if found:
                        break
                # Not found, save empty artwork
                if not found:
                    App().art.save_album_artwork(Album(album_id), None)
        except Exception as e:
            Logger.error("DownloaderArt::__cache_albums_artwork: %s" % e)
        self.__in_albums_download = False

    def __on_load_google_content(self, uri, loaded, content):
        """
            Extract uris from content
            @param uri as str
            @param loaded as bool
            @param content as bytes
        """
        try:
            if not loaded:
                emit_signal(self, "uri-artwork-found", None)
                return
            decode = json.loads(content.decode("utf-8"))
            results = []
            for item in decode["items"]:
                if item["link"] is not None:
                    results.append((item["link"], "Google"))
            emit_signal(self, "uri-artwork-found", results)
        except Exception as e:
            emit_signal(self, "uri-artwork-found", None)
            Logger.error("DownloaderArt::__on_load_google_content(): %s: %s"
                         % (e, content))

    def __on_load_startpage_content(self, uri, loaded, content):
        """
            Extract uris from content
            @param uri as str
            @param loaded as bool
            @param content as bytes
        """
        import re

        def search_in_data(lines, found_uris=[]):
            if lines:
                line = lines.pop(0)
                # Do not call findall if nothing to find
                if line.find("oiu=") != -1:
                    res = re.findall(r'.*oiu=([^&]*).*', line)
                    for data in res:
                        uri = GLib.uri_unescape_string(data, "")
                        if uri in found_uris or uri is None:
                            continue
                        found_uris.append(uri)
                GLib.idle_add(search_in_data, lines, found_uris)
            else:
                results = [(uri, "Startpage") for uri in found_uris]
                emit_signal(self, "uri-artwork-found", results)

        try:
            if not loaded:
                emit_signal(self, "uri-artwork-found", None)
                return
            lines = content.decode("utf-8").splitlines()
            search_in_data(lines)
        except Exception as e:
            emit_signal(self, "uri-artwork-found", None)
            Logger.error("DownloaderArt::__on_load_startpage_content(): %s"
                         % e)
