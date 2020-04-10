# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

import json
from time import time
from random import choice, shuffle
from locale import getdefaultlocale

from lollypop.logger import Logger
from lollypop.utils import get_default_storage_type
from lollypop.sqlcursor import SqlCursor
from lollypop.helper_web_spotify import SpotifyWebHelper
from lollypop.define import App, StorageType


class SpotifyWebService(SpotifyWebHelper):
    """
        Search for Spotify
    """
    __MIN_ITEMS_PER_STORAGE_TYPE = 20
    __MAX_ITEMS_PER_STORAGE_TYPE = 50

    def __init__(self):
        """
            Init object
        """
        SpotifyWebHelper.__init__(self)
        self.__is_running = False
        self.__cancellable = Gio.Cancellable()

    def start(self):
        """
            Populate DB in a background task
        """
        if self.__is_running:
            return
        App().task_helper.run(self.__populate_db)
        return True

    def search_similar_albums(self, cancellable):
        """
            Add similar albums to DB
            @param cancellable as Gio.Cancellable
        """
        Logger.info("Get similar albums")
        from lollypop.similars_spotify import SpotifySimilars
        similars = SpotifySimilars()
        try:
            storage_type = get_default_storage_type()
            artists = App().artists.get_randoms(
                self.__MAX_ITEMS_PER_STORAGE_TYPE, storage_type)
            artist_names = [name for (aid, name, sortname) in artists]
            similar_ids = similars.get_similar_artist_ids(artist_names,
                                                          cancellable)
            # Add albums
            shuffle(similar_ids)
            for similar_id in similar_ids[:self.__MAX_ITEMS_PER_STORAGE_TYPE]:
                albums_payload = self.__get_artist_albums_payload(similar_id,
                                                                  cancellable)
                if albums_payload:
                    self.save_albums_payload_to_db(
                                           [choice(albums_payload)],
                                           StorageType.SPOTIFY_SIMILARS,
                                           True,
                                           cancellable)
        except Exception as e:
            Logger.warning("SpotifyWebService::search_similar_albums(): %s", e)

    def search_new_releases(self, cancellable):
        """
            Get new released albums from spotify
            @param cancellable as Gio.Cancellable
        """
        Logger.info("Get new releases")
        try:
            locale = getdefaultlocale()[0][0:2]
            token = App().ws_director.token_ws.get_token("SPOTIFY",
                                                         cancellable)
            bearer = "Bearer %s" % token
            headers = ["Authorization", bearer]
            uri = "https://api.spotify.com/v1/browse/new-releases"
            uris = ["%s?country=%s" % (uri, locale), uri]
            for uri in uris:
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                (status,
                 data) = App().task_helper.load_uri_content_sync_with_headers(
                    uri, headers, cancellable)
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    self.save_albums_payload_to_db(
                                             decode["albums"]["items"],
                                             StorageType.SPOTIFY_NEW_RELEASES,
                                             True,
                                             cancellable)
                    # Check if storage type needs to be updated
                    # Check if albums newer than a week are enough
                    timestamp = time() - 604800
                    newer_albums = App().albums.get_newer_for_storage_type(
                                             StorageType.SPOTIFY_NEW_RELEASES,
                                             timestamp)
                    if len(newer_albums) >= self.__MIN_ITEMS_PER_STORAGE_TYPE:
                        break
        except Exception as e:
            Logger.warning("SpotifyWebService::search_new_releases(): %s", e)

    def get_similar_artists(self, artist_id, cancellable):
        """
           Get similar artists
           @param artist_id as str
           @param cancellable as Gio.Cancellable
           @return [(str, str)] : list of (artist, cover_uri)
        """
        artists = []
        try:
            token = App().ws_director.token_ws.get_token("SPOTIFY",
                                                         cancellable)
            bearer = "Bearer %s" % token
            headers = [("Authorization", bearer)]
            uri = "https://api.spotify.com/v1/artists/%s/related-artists" %\
                artist_id
            (status,
             data) = App().task_helper.load_uri_content_sync_with_headers(
                    uri, headers, cancellable)
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]:
                    try:
                        image_uri = item["images"][1]["url"]
                    except:
                        image_uri = None
                    artists.append((item["id"],
                                    item["name"],
                                    image_uri))
        except Exception as e:
            Logger.error("SpotifyWebService::get_similar_artists(): %s", e)
        return artists

    def stop(self):
        """
            Stop db populate
        """
        if not self.__cancellable.is_cancelled():
            self.__cancellable.cancel()

    @property
    def is_running(self):
        """
            Return populate status
            @return bool
        """
        return self.__is_running

#######################
# PRIVATE             #
#######################
    def __populate_db(self):
        """
            Populate DB in a background task
        """
        try:
            Logger.info("Spotify download started")
            self.__is_running = True
            self.__cancellable = Gio.Cancellable()
            storage_types = []
            # Check if storage type needs to be updated
            # Check if albums newer than a week are enough
            timestamp = time() - 604800
            for storage_type in [StorageType.SPOTIFY_SIMILARS,
                                 StorageType.SPOTIFY_NEW_RELEASES]:
                newer_albums = App().albums.get_newer_for_storage_type(
                                                           storage_type,
                                                           timestamp)
                if len(newer_albums) < self.__MIN_ITEMS_PER_STORAGE_TYPE:
                    storage_types.append(storage_type)
            # Update needed storage types
            if storage_types:
                for storage_type in storage_types:
                    if self.__cancellable.is_cancelled():
                        raise Exception("cancelled")
                    if storage_type == StorageType.SPOTIFY_NEW_RELEASES:
                        self.search_new_releases(self.__cancellable)
                    else:
                        self.search_similar_albums(self.__cancellable)
                self.clean_old_albums(storage_types)
                App().artists.update_featuring()
        except Exception as e:
            Logger.warning("SpotifyWebService::__populate_db(): %s", e)
        self.__is_running = False
        Logger.info("Spotify download finished")

    def clean_old_albums(self, storage_types):
        """
            Clean old albums from DB
            @param storage_types as [StorageType]
        """
        SqlCursor.add(App().db)
        # Remove older albums
        for storage_type in storage_types:
            # If too many albums, do some cleanup
            count = App().albums.get_count_for_storage_type(storage_type)
            diff = count - self.__MAX_ITEMS_PER_STORAGE_TYPE
            if diff > 0:
                album_ids = App().albums.get_oldest_for_storage_type(
                    storage_type, diff)
                for album_id in album_ids:
                    # EPHEMERAL with not tracks will be cleaned below
                    App().albums.set_storage_type(album_id,
                                                  StorageType.EPHEMERAL)
                    App().tracks.remove_album(album_id, False)
        # On cancel, clean not needed, done in Application::quit()
        if not self.__cancellable.is_cancelled():
            App().tracks.clean(False)
            App().albums.clean(False)
            App().artists.clean(False)
        SqlCursor.commit(App().db)
        SqlCursor.remove(App().db)

    def __get_artist_albums_payload(self, spotify_id, cancellable):
        """
            Get albums payload for artist
            @param spotify_id as str
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            token = App().ws_director.token_ws.get_token("SPOTIFY",
                                                         cancellable)
            bearer = "Bearer %s" % token
            headers = [("Authorization", bearer)]
            uri = "https://api.spotify.com/v1/artists/%s/albums" % spotify_id
            (status,
             data) = App().task_helper.load_uri_content_sync_with_headers(
                    uri, headers, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                return decode["items"]
        except Exception as e:
            Logger.warning(
                "SpotifyWebService::__get_artist_albums_payload(): %s", e)
        return None
