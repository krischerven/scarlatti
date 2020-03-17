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

from gi.repository import Gst, GLib, GObject

from pickle import load
from time import time

from lollypop.player_albums import AlbumsPlayer
from lollypop.player_auto_random import AutoRandomPlayer
from lollypop.player_auto_similar import AutoSimilarPlayer
from lollypop.player_bin import BinPlayer
from lollypop.player_queue import QueuePlayer
from lollypop.player_linear import LinearPlayer
from lollypop.player_shuffle import ShufflePlayer
from lollypop.player_radio import RadioPlayer
from lollypop.player_transitions import TransitionsPlayer
from lollypop.radios import Radios
from lollypop.logger import Logger
from lollypop.objects_track import Track
from lollypop.objects_radio import Radio
from lollypop.define import App, Type, LOLLYPOP_DATA_PATH
from lollypop.utils import emit_signal


class Player(GObject.GObject, AlbumsPlayer, BinPlayer, AutoRandomPlayer,
             AutoSimilarPlayer, QueuePlayer, RadioPlayer, LinearPlayer,
             ShufflePlayer, TransitionsPlayer):
    """
        Player object used to manage playback and playlists
    """

    __gsignals__ = {
        "current-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "duration-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "loading-changed": (GObject.SignalFlags.RUN_FIRST, None,
                            (bool, GObject.TYPE_PYOBJECT)),
        "next-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "prev-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "seeked": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "status-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "volume-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "queue-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "playback-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "rate-changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int))
    }

    def __init__(self):
        """
            Init player
        """
        GObject.GObject.__init__(self)
        AlbumsPlayer.__init__(self)
        AutoRandomPlayer.__init__(self)
        AutoSimilarPlayer.__init__(self)
        BinPlayer.__init__(self)
        QueuePlayer.__init__(self)
        LinearPlayer.__init__(self)
        ShufflePlayer.__init__(self)
        RadioPlayer.__init__(self)
        TransitionsPlayer.__init__(self)
        self.__stop_after_track_id = None
        App().settings.connect("changed::repeat", self.update_next_prev)

    def load(self, track):
        """
            Stop current track, load track id and play it
            @param track as Track
        """
        if isinstance(track, Radio):
            RadioPlayer.load(self, track)
        elif TransitionsPlayer.load(self, track):
            pass
        else:
            BinPlayer.load(self, track)

    def prev(self):
        """
            Play previous track
        """
        if self.position / Gst.SECOND > 2:
            self.seek(0)
            emit_signal(self, "current-changed")
            if not self.is_playing:
                self.play()
        elif self._prev_track.id is not None:
            self.load(self._prev_track)
        else:
            self.stop()

    def next(self):
        """
            Play next track
        """
        if self._next_track.id is not None:
            self.__scrobble(self._current_track, self._start_time)
            self.load(self._next_track)
        else:
            self.stop()

    def stop_after(self, track_id):
        """
            Tell player to stop after track_id
            @param track_id as int
        """
        self.__stop_after_track_id = track_id

    def get_current_artists(self):
        """
            Get current artist
            @return artist as string
        """
        artist_ids = self._current_track.album.artist_ids
        if artist_ids[0] == Type.COMPILATIONS:
            artists = ", ".join(self._current_track.artists)
        else:
            artists = ", ".join(self._current_track.album_artists)
        return artists

    def restore_state(self):
        """
            Restore player state
        """
        try:
            if App().settings.get_value("save-state"):
                self._current_playback_track = Track(
                    load(open(LOLLYPOP_DATA_PATH + "/track_id.bin", "rb")))
                self.set_queue(load(open(LOLLYPOP_DATA_PATH +
                                         "/queue.bin", "rb")))
                albums = load(open(LOLLYPOP_DATA_PATH + "/Albums.bin", "rb"))
                playlist_ids = load(open(LOLLYPOP_DATA_PATH +
                                         "/playlist_ids.bin", "rb"))
                (is_playing, was_party) = load(open(LOLLYPOP_DATA_PATH +
                                                    "/player.bin", "rb"))
                if playlist_ids and playlist_ids[0] == Type.RADIOS:
                    radios = Radios()
                    track = Track()
                    name = radios.get_name(self._current_playback_track.id)
                    uri = radios.get_uri(self._current_playback_track.id)
                    track.set_radio(name, uri)
                    self.load(track)
                elif self._current_playback_track.uri:
                    if albums:
                        if was_party:
                            App().lookup_action("party").change_state(
                                GLib.Variant("b", True))
                        else:
                            self._albums = load(open(
                                                LOLLYPOP_DATA_PATH +
                                                "/Albums.bin",
                                                "rb"))
                        # Load track from player albums
                        index = self.album_ids.index(
                            self._current_playback_track.album.id)
                        for track in self._albums[index].tracks:
                            if track.id == self._current_playback_track.id:
                                self._load_track(track)
                                break
                    if is_playing:
                        self.play()
                    else:
                        self.pause()
                    position = load(open(LOLLYPOP_DATA_PATH + "/position.bin",
                                    "rb"))
                    self.seek(position)
                else:
                    Logger.info("Player::restore_state(): track missing")
        except Exception as e:
            Logger.error("Player::restore_state(): %s" % e)

    def set_party(self, party):
        """
            Set party mode on if party is True
            Play a new random track if not already playing
            @param party as bool
        """
        ShufflePlayer.set_party(self, party)
        self.update_crossfading()

    def set_prev(self):
        """
            Set previous track
        """
        if isinstance(self.current_track, Radio):
            return
        try:
            if App().settings.get_value("shuffle") or self.is_party:
                prev_track = ShufflePlayer.prev(self)
            else:
                prev_track = LinearPlayer.prev(self)
            self._prev_track = prev_track
            emit_signal(self, "prev-changed")
        except Exception as e:
            Logger.error("Player::set_prev(): %s" % e)

    def set_next(self):
        """
            Play next track
        """
        if isinstance(self.current_track, Radio) or\
                self._current_track.id == self.__stop_after_track_id:
            self._next_track = Track()
            return
        try:
            next_track = QueuePlayer.next(self)
            if next_track.id is None:
                if App().settings.get_value("shuffle") or self.is_party:
                    next_track = ShufflePlayer.next(self)
                else:
                    next_track = LinearPlayer.next(self)
            self._next_track = next_track
            if next_track.is_web:
                App().task_helper.run(self._load_from_web, next_track, False)
            emit_signal(self, "next-changed")
        except Exception as e:
            Logger.error("Player::set_next(): %s" % e)

    def update_next_prev(self, *ignore):
        """
            Update next/prev
            @param player as Player
        """
        if self._current_track.id is not None:
            if not self.is_party:
                self.set_next()
            self.set_prev()

    @property
    def next_track(self):
        """
            Current track
        """
        return self._next_track

    @property
    def prev_track(self):
        """
            Current track
        """
        return self._prev_track

    @property
    def stop_after_track_id(self):
        """
            Get stop after track id
            @return int
        """
        return self.__stop_after_track_id

#######################
# PROTECTED           #
#######################
    def _on_track_finished(self, track):
        """
            Scrobble track, update last played time and increment popularity
            @param track as Track
        """
        self.__scrobble(track, self._start_time)
        if track.id is not None and track.id >= 0:
            App().tracks.set_listened_at(track.id, int(time()))
            # Increment popularity
            App().tracks.set_more_popular(track.id)
            # In party mode, linear popularity
            if self.is_party:
                pop_to_add = 1
            # In normal mode, based on tracks count
            else:
                count = track.album.tracks_count
                pop_to_add = int(App().albums.max_count / count)
            App().albums.set_more_popular(track.album_id, pop_to_add)

    def _on_stream_start(self, bus, message):
        """
            On stream start, set next and previous track
        """
        self.__stop_after_track_id = None
        if self.is_in_queue(self._current_track.id):
            self.remove_from_queue(self._current_track.id)
        else:
            self._current_playback_track = self._current_track
        ShufflePlayer._on_stream_start(self, bus, message)
        BinPlayer._on_stream_start(self, bus, message)
        self.set_next()
        self.set_prev()

#######################
# PRIVATE             #
#######################
    def __scrobble(self, track, finished_start_time):
        """
            Scrobble on lastfm
            @param track as Track
            @param finished_start_time as int
        """
        played = time() - finished_start_time
        # Last.fm policy, force it for ListenBrainz too
        if track.duration < 30000:
            return
        # We can listen if the track has been played
        # for at least half its duration, or for 4 minutes
        if played >= track.duration / 2000 or played >= 240:
            for scrobbler in App().scrobblers:
                if scrobbler.available:
                    scrobbler.listen(track, int(finished_start_time))
