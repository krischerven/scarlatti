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

from gi.repository import Gst, GLib

from pickle import load
from random import choice, shuffle
from lollypop.player_bin import BinPlayer
from lollypop.player_queue import QueuePlayer
from lollypop.player_linear import LinearPlayer
from lollypop.player_shuffle import ShufflePlayer
from lollypop.player_radio import RadioPlayer
from lollypop.player_similars import SimilarsPlayer
from lollypop.radios import Radios
from lollypop.logger import Logger
from lollypop.objects_track import Track
from lollypop.objects_album import Album
from lollypop.objects_radio import Radio
from lollypop.define import App, Type, LOLLYPOP_DATA_PATH
from lollypop.utils import emit_signal


class Player(BinPlayer, QueuePlayer, RadioPlayer,
             LinearPlayer, ShufflePlayer, SimilarsPlayer):
    """
        Player object used to manage playback and playlists
    """

    def __init__(self):
        """
            Init player
        """
        BinPlayer.__init__(self)
        QueuePlayer.__init__(self)
        LinearPlayer.__init__(self)
        ShufflePlayer.__init__(self)
        RadioPlayer.__init__(self)
        SimilarsPlayer.__init__(self)
        self.__stop_after_track_id = None
        self.update_crossfading()
        App().settings.connect("changed::repeat", self.update_next_prev)

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
            self._scrobble(self._current_track, self._start_time)
            self.load(self._next_track)
        else:
            self.stop()

    def load(self, track, play=True):
        """
            Stop current track, load track id and play it
            @param track as Track
            @param play as bool, ignored for radios
        """
        if isinstance(track, Radio):
            RadioPlayer.load(self, track, play)
        else:
            if play:
                BinPlayer.load(self, track)
            else:
                BinPlayer._load_track(self, track)
                emit_signal(self, "current-changed")

    def add_album(self, album):
        """
            Add album to player
            @param album as Album
        """
        # Merge album if previous is same
        if self._albums and self._albums[-1].id == album.id:
            tracks = list(set(self._albums[-1].tracks) | set(album.tracks))
            self._albums[-1].set_tracks(tracks)
        else:
            self._albums.append(album)
        emit_signal(self, "playback-changed")

    def remove_album(self, album):
        """
            Remove album from albums
            @param album as Album
        """
        try:
            if album not in self._albums:
                return
            if self._current_track.album == album:
                self.skip_album()
            else:
                self.update_next_prev()
            self._albums.remove(album)
            emit_signal(self, "playback-changed")
        except Exception as e:
            Logger.error("Player::remove_album(): %s" % e)

    def remove_album_by_id(self, album_id):
        """
            Remove all instance of album with id from albums
            @param album_id as int
        """
        try:
            for album in self._albums:
                if album.id == album_id:
                    self.remove_album(album)
            emit_signal(self, "playback-changed")
        except Exception as e:
            Logger.error("Player::remove_album_by_id(): %s" % e)

    def play_album(self, album):
        """
            Play album
            @param album as Album
        """
        self.play_album_for_albums(album, [album])

    def play_track_for_albums(self, track, albums):
        """
            Play track and set albums as current playlist
            @param albums as [Album]
            @param track as Track
        """
        if self.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        self._albums = albums
        self.load(track)
        emit_signal(self, "playback-changed")

    def play_album_for_albums(self, album, albums):
        """
            Play album and set albums as current playlist
            @param album as Album
            @param albums as [Album]
        """
        if self.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        if App().settings.get_value("shuffle"):
            self.__play_shuffle_tracks(album, albums)
        else:
            self.__play_albums(album, albums)
        emit_signal(self, "playback-changed")

    def play_albums(self, albums):
        """
            Play albums
            @param album as [Album]
        """
        if not albums:
            return
        if App().settings.get_value("shuffle"):
            album = choice(albums)
        else:
            album = albums[0]
        self.play_album_for_albums(album, albums)

    def play_uris(self, uris):
        """
            Play uris
            @param uris as [str]
        """
        # First get tracks
        tracks = []
        for uri in uris:
            track_id = App().tracks.get_id_by_uri(uri)
            if track_id is not None:
                tracks.append(Track(track_id))
        # Then get album ids
        album_ids = {}
        for track in tracks:
            if track.album.id in album_ids.keys():
                album_ids[track.album.id].append(track)
            else:
                album_ids[track.album.id] = [track]
        # Create albums with tracks
        play = True
        for album_id in album_ids.keys():
            album = Album(album_id)
            album.set_tracks(album_ids[album_id])
            if play:
                self.play_album(album)
            else:
                self.add_album(album)
        emit_signal(self, "playback-changed")

    def set_albums(self, albums):
        """
            Set player albums
        """
        self._albums = albums

    def clear_albums(self):
        """
            Clear all albums
        """
        self._albums = []
        emit_signal(self, "playback-changed")

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
                    self.load(track, is_playing)
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
                    self.seek(position / Gst.SECOND)
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
            self.__stop_after_track_id = None
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

    def skip_album(self):
        """
            Skip current album
        """
        try:
            # In party or shuffle, just update next track
            if self.is_party or App().settings.get_value("shuffle"):
                self.set_next()
                # We send this signal to update next popover
                emit_signal(self, "queue-changed")
            elif self._current_track.id is not None:
                index = self.album_ids.index(
                    App().player._current_playback_track.album.id)
                if index + 1 >= len(self._albums):
                    next_album = self._albums[0]
                else:
                    next_album = self._albums[index + 1]
                self.load(next_album.tracks[0])
        except Exception as e:
            Logger.error("Player::skip_album(): %s" % e)

    def update_next_prev(self, *ignore):
        """
            Update next/prev
            @param player as Player
        """
        if self._current_track.id is not None:
            if not self.is_party:
                self.set_next()
            self.set_prev()

    def update_crossfading(self):
        """
            Calculate if crossfading is needed
        """
        mix = App().settings.get_value("smooth-transitions")
        party_mix = App().settings.get_value("party-mix")
        self._crossfading = (mix and not party_mix) or\
                            (mix and party_mix and self.is_party)

    def track_in_playback(self, track):
        """
            True if track present in current playback
            @param track as Track
            @return bool
        """
        for album in self._albums:
            if album.id == track.album.id:
                for track_id in album.track_ids:
                    if track.id == track_id:
                        return True
        return False

    def get_albums_for_id(self, album_id):
        """
            Get albums for id
            @param album_id as int
            @return [Album]
        """
        return [album for album in self._albums if album.id == album_id]

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
    def albums(self):
        """
            Return albums
            @return albums as [Album]
        """
        return self._albums

    @property
    def album_ids(self):
        """
            Return albums ids
            @return albums ids as [int]
        """
        return [album.id for album in self._albums]

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
    def _on_stream_start(self, bus, message):
        """
            On stream start, set next and previous track
        """
        if self.track_in_queue(self._current_track):
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
    def __play_shuffle_albums(self, album, albums):
        """
            Start shuffle albums playback. Prepend album if not None
            @param album as Album
            @param albums as [albums]
        """
        track = None
        if album is None:
            album = choice(albums)
        else:
            self._albums = [album]
            albums.remove(album)
        shuffle(albums)
        self._albums += albums
        if album.tracks:
            track = album.tracks[0]
        if track is not None:
            self.load(track)

    def __play_shuffle_tracks(self, album, albums):
        """
            Start shuffle tracks playback.
            @param album as Album
            @param albums as [albums]
        """
        if album is None:
            album = choice(albums)
        if album.tracks:
            track = choice(album.tracks)
        else:
            track = None
        self._albums = albums
        if track is not None:
            self.load(track)

    def __play_albums(self, album, albums):
        """
            Start albums playback.
            @param album as Album
            @param albums as [albums]
        """
        if album is None:
            album = albums[0]
        if album.tracks:
            track = album.tracks[0]
        else:
            track = None
        self._albums = albums
        if track is not None:
            self.load(track)
