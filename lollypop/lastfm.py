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

import gi
gi.require_version("Secret", "1")
from gi.repository import Gio, GLib, GObject

from gettext import gettext as _

try:
    from gi.repository import Secret
except Exception as e:
    print(e)
    print(_("Last.fm authentication disabled"))
    Secret = None

from pylast import LastFMNetwork, LibreFMNetwork, md5, WSError
from pylast import SessionKeyGenerator
from locale import getdefaultlocale
from pickle import load, dump
import re

from lollypop.define import App, LOLLYPOP_DATA_PATH
from lollypop.objects import Track
from lollypop.utils import get_network_available
from lollypop.logger import Logger
from lollypop.goa import GoaSyncedAccount


class LastFM(GObject.Object, LastFMNetwork, LibreFMNetwork):
    """
       Lastfm:
       We recommend you don"t distribute the API key and secret with your app,
       and that you ask users who want to build it to apply for a key of
       their own. We don"t believe that this would violate the terms of most
       open-source licenses.
       That said, we can"t stop you from distributing the key and secret if you
       want, and if your app isn"t written in a compiled language, you don"t
       really have much option :).
    """
    __gsignals__ = {
        "new-artist": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self, name):
        """
            Init lastfm support
            @param name as str
        """
        GObject.Object.__init__(self)
        self.__name = name
        self.__login = ""
        self.session_key = ""
        self.__password = None
        self.__goa = None
        self.__queue_id = None
        try:
            self.__queue = load(
                open(LOLLYPOP_DATA_PATH + "/%s_queue.bin" % self.__name, "rb"))
        except Exception as e:
            Logger.info("LastFM::__init__(): %s", e)
            self.__queue = []
        if name == "librefm":
            LibreFMNetwork.__init__(self)
            Logger.debug("LibreFMNetwork.__init__()")
        else:
            self.__goa = GoaSyncedAccount("Last.fm")
            self.__goa.connect("account-switched",
                               self.on_goa_account_switched)
            if self.is_goa:
                Logger.debug("LastFMNetwork.__init__(goa.)")
                auth = self.__goa.oauth2_based
                self.__API_KEY = auth.props.client_id
                self.__API_SECRET = auth.props.client_secret
            else:
                Logger.debug("LastFMNetwork.__init__(secret)")
                self.__API_KEY = "7a9619a850ccf7377c46cf233c51e3c6"
                self.__API_SECRET = "9254319364d73bec6c59ace485a95c98"
            LastFMNetwork.__init__(self,
                                   api_key=self.__API_KEY,
                                   api_secret=self.__API_SECRET)
        self.connect()
        Gio.NetworkMonitor.get_default().connect("notify::network-available",
                                                 self.__on_network_available)

    def connect(self, full_sync=False, callback=None, *args):
        """
            Connect service
            @param full_sync as bool
            @param callback as function
        """
        if self.is_goa:
            App().task_helper.run(self.__connect, full_sync)
        else:
            from lollypop.helper_passwords import PasswordsHelper
            helper = PasswordsHelper()
            helper.get(self.__name,
                       self.__on_get_password,
                       full_sync,
                       callback,
                       *args)

    def save(self):
        """
            Save queue to disk
        """
        with open(LOLLYPOP_DATA_PATH + "/%s_queue.bin" % self.__name,
                  "wb") as f:
            dump(list(self.__queue), f)

    def get_artist_artwork_uri(self, artist):
        """
            Get artist infos
            @param artist as str
            @return uri as str/None
        """
        if not get_network_available("LASTFM"):
            return (None, None, None)
        last_artist = self.get_artist(artist)
        uri = last_artist.get_cover_image(3)
        return uri

    def get_artist_bio(self, artist):
        """
            Get artist infos
            @param artist as str
            @return content as str/None
        """
        if not get_network_available("LASTFM"):
            return None
        last_artist = self.get_artist(artist)
        try:
            content = last_artist.get_bio_content(
                language=getdefaultlocale()[0][0:2])
        except:
            content = last_artist.get_bio_content()
        content = re.sub(r"<.*Last.fm.*>.", "", content)
        return content.encode(encoding="UTF-8")

    def listen(self, track, timestamp):
        """
            Submit a listen for a track (scrobble)
            @param track as Track
            @param timestamp as int
        """
        if not get_network_available("LASTFM") and get_network_available():
            return
        if App().settings.get_value("disable-scrobbling") or\
                not get_network_available("LASTFM"):
            self.__queue.append((track, timestamp))
        elif track.id is not None and track.id >= 0 and self.available:
            self.__clean_queue()
            App().task_helper.run(
                       self.__listen,
                       track.artists[0],
                       track.album_name,
                       track.title,
                       timestamp,
                       track.mb_track_id)

    def playing_now(self, track):
        """
            Submit a playing now notification for a track
            @param track as Track
        """
        if not get_network_available("LASTFM") and get_network_available():
            return
        if App().settings.get_value("disable-scrobbling"):
            return
        if track.id is not None and track.id >= 0 and self.available:
            App().task_helper.run(
                       self.__playing_now,
                       track.artists[0],
                       track.album_name,
                       track.title,
                       int(track.duration),
                       track.mb_track_id)

    def love(self, artist, title):
        """
            Love track
            @param artist as string
            @param title as string
            @thread safe
        """
        # Love the track on lastfm
        if get_network_available("LASTFM") and self.available:
            track = self.get_track(artist, title)
            try:
                track.love()
            except Exception as e:
                Logger.error("Lastfm::love(): %s" % e)

    def unlove(self, artist, title):
        """
            Unlove track
            @param artist as string
            @param title as string
            @thread safe
        """
        # Love the track on lastfm
        if get_network_available("LASTFM") and self.available:
            track = self.get_track(artist, title)
            try:
                track.unlove()
            except Exception as e:
                Logger.error("Lastfm::unlove(): %s" % e)

    def get_similar_artists(self, artist, cancellable):
        """
            Search similar artists
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return [str]
        """
        artists = []
        try:
            artist_item = self.get_artist(artist)
            for similar_item in artist_item.get_similar():
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                artists.append(similar_item.item.name)
        except Exception as e:
            Logger.error("LastFM::get_similar_artists(): %s", e)
        return artists

    def search_similar_artists(self, artist, cancellable):
        """
            Search similar artists
            @param artist as str
            @param cancellable as Gio.Cancellable
        """
        try:
            found = False
            artist_item = self.get_artist(artist)
            for similar_item in artist_item.get_similar():
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                found = True
                artist_name = similar_item.item.name
                cover_uri = similar_item.item.get_cover_image()
                GLib.idle_add(self.emit, "new-artist", artist_name, cover_uri)
        except Exception as e:
            Logger.error("LastFM::search_similar_artists(): %s", e)
        if not found:
            GLib.idle_add(self.emit, "new-artist", None, None)

    def on_goa_account_switched(self, obj):
        """
            Callback for GoaSyncedAccount signal "account-switched"
            @param obj as GoaSyncedAccount
        """
        self.connect()

    def set_loved(self, track, loved):
        """
            Add or remove track from loved playlist on Last.fm
            @param track as Track
            @param loved as bool
        """
        if get_network_available("LASTFM") and self.available:
            if loved == 1:
                self.love(",".join(track.artists), track.name)
            else:
                self.unlove(",".join(track.artists), track.name)

    @property
    def can_love(self):
        """
            True if engine can love
            @return bool
        """
        return True

    @property
    def is_goa(self):
        """
            True if using Gnome Online Account
        """
        return self.__goa is not None and self.__goa.has_account

    @property
    def available(self):
        """
            Return True if Last.fm/Libre.fm submission is available
            @return bool
        """
        if not self.session_key:
            return False
        if self.is_goa:
            music_disabled = self.__goa.account.props.music_disabled
            Logger.debug("Last.fm GOA scrobbling disabled: %s" %
                         music_disabled)
            return not music_disabled
        return True

#######################
# PRIVATE             #
#######################
    def __clean_queue(self):
        """
            Send tracks in queue
        """
        def queue():
            if self.__queue:
                (track, timestamp) = self.__queue.pop(0)
                self.listen(track, timestamp)
                return True
            self.__queue_id = None

        if self.__queue_id is None:
            self.__queue_id = GLib.timeout_add(1000, queue)

    def __connect(self, full_sync=False):
        """
            Connect service
            @param full_sync as bool
            @thread safe
        """
        if not get_network_available("LASTFM"):
            return
        try:
            self.session_key = ""
            if self.is_goa:
                auth = self.__goa.oauth2_based
                self.api_key = auth.props.client_id
                self.api_secret = auth.props.client_secret
                self.session_key = auth.call_get_access_token_sync(None)[0]
            else:
                skg = SessionKeyGenerator(self)
                self.session_key = skg.get_session_key(
                    username=self.__login,
                    password_hash=md5(self.__password))
            if full_sync:
                App().task_helper.run(self.__populate_loved_tracks)
            track = App().player.current_track
            self.playing_now(track)
        except Exception as e:
            Logger.debug("LastFM::__connect(): %s" % e)

    def __listen(self, artist, album, title, timestamp, mb_track_id):
        """
            Scrobble track
            @param artist as str
            @param title as str
            @param album_title as str
            @param timestamp as int
            @param duration as int
            @param mb_track_id as str
            @thread safe
        """
        Logger.debug("LastFM::__listen(): %s, %s, %s, %s, %s" % (
                                                            artist,
                                                            album,
                                                            title,
                                                            timestamp,
                                                            mb_track_id))
        try:
            self.scrobble(artist=artist,
                          album=album,
                          title=title,
                          timestamp=timestamp,
                          mbid=mb_track_id)
        except WSError:
            pass
        except Exception as e:
            Logger.error("LastFM::__listen(): %s" % e)

    def __playing_now(self, artist, album, title, duration, mb_track_id):
        """
            Now playing track
            @param artist as str
            @param title as str
            @param album as str
            @param duration as int
            @thread safe
        """
        try:
            self.update_now_playing(artist=artist,
                                    album=album,
                                    title=title,
                                    duration=duration,
                                    mbid=mb_track_id)
            Logger.debug("LastFM::__playing_now(): %s, %s, %s, %s, %s" % (
                artist, album, title, duration, mb_track_id))
        except WSError:
            pass
        except Exception as e:
            Logger.error("LastFM::__playing_now(): %s" % e)

    def __populate_loved_tracks(self):
        """
            Populate loved tracks playlist
        """
        if not self.available:
            return
        try:
            user = self.get_user(self.__login)
            for loved in user.get_loved_tracks(limit=None):
                artist = str(loved.track.artist)
                title = str(loved.track.title)
                track_id = App().tracks.search_track(artist, title)
                if track_id is None:
                    Logger.warning(
                        "LastFM::__populate_loved_tracks(): %s, %s" % (
                            artist, title))
                else:
                    Track(track_id).set_loved(1)
        except Exception as e:
            Logger.error("LastFM::__populate_loved_tracks: %s" % e)

    def __on_get_password(self, attributes, password,
                          name, full_sync, callback, *args):
        """
             Set password label
             @param attributes as {}
             @param password as str
             @param name as str
             @param full_sync as bool
             @param callback as function
        """
        if attributes is None:
            Logger.error("LastFM::__on_get_password(): no attributes")
            return
        self.__login = attributes["login"]
        self.__password = password
        if get_network_available("LASTFM"):
            App().task_helper.run(self.__connect, full_sync,
                                  callback=(callback, *args))

    def __on_network_available(self, monitor, spec):
        """
            Connect if network is available and not already connected
            @param monitory as Gio.NetworkMonitor
            @param value as GSpec
        """
        value = monitor.get_property("network-available")
        if value and not self.available:
            self.connect()
