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

from gi.repository import Gst, GstAudio, GstPbutils, GLib, Gio

from time import time

from lollypop.player_base import BasePlayer
from lollypop.tagreader import TagReader, Discoverer
from lollypop.player_plugins import PluginsPlayer
from lollypop.define import GstPlayFlags, App
from lollypop.codecs import Codecs
from lollypop.logger import Logger
from lollypop.objects_track import Track
from lollypop.objects_radio import Radio
from lollypop.utils import emit_signal, get_network_available


class BinPlayer(BasePlayer):
    """
        Gstreamer bin player
    """

    def __init__(self):
        """
            Init playbin
        """
        BasePlayer.__init__(self)
        self.__cancellable = Gio.Cancellable()
        self.__codecs = Codecs()
        self._playbin = self.__playbin1 = Gst.ElementFactory.make(
            "playbin", "player")
        self.__playbin2 = Gst.ElementFactory.make("playbin", "player")
        self._plugins = self._plugins1 = PluginsPlayer(self.__playbin1)
        self._plugins2 = PluginsPlayer(self.__playbin2)
        self._playbin.connect("notify::volume", self.__on_volume_changed)
        for playbin in [self.__playbin1, self.__playbin2]:
            flags = playbin.get_property("flags")
            flags &= ~GstPlayFlags.GST_PLAY_FLAG_VIDEO
            playbin.set_property("flags", flags)
            playbin.set_property("buffer-size", 5 << 20)
            playbin.set_property("buffer-duration", 10 * Gst.SECOND)
            playbin.connect("about-to-finish",
                            self._on_stream_about_to_finish)
            bus = playbin.get_bus()
            bus.add_signal_watch()
            bus.connect("message::error", self._on_bus_error)
            bus.connect("message::eos", self._on_bus_eos)
            bus.connect("message::element", self._on_bus_element)
            bus.connect("message::stream-start", self._on_stream_start)
            bus.connect("message::tag", self._on_bus_message_tag)
        self._start_time = 0

    def get_status(self):
        """
            Playback status
            @return Gstreamer state
        """
        ok, state, pending = self._playbin.get_state(Gst.CLOCK_TIME_NONE)
        if ok == Gst.StateChangeReturn.ASYNC:
            state = pending
        elif (ok != Gst.StateChangeReturn.SUCCESS):
            state = Gst.State.NULL
        return state

    def load(self, track):
        """
            Stop current track, load track id and play it
            @param track as Track
        """
        if self._crossfading and\
           self._current_track.id is not None and\
           self.is_playing and\
           not isinstance(track, Radio):
            duration = App().settings.get_value(
                "transition-duration").get_int32()
            self.__do_crossfade(duration, track)
        else:
            self.__load(track)

    def play(self):
        """
            Change player state to PLAYING
        """
        # No current playback, song in queue
        if self._current_track.id is None:
            if self._next_track.id is not None:
                self.load(self._next_track)
        else:
            self._playbin.set_state(Gst.State.PLAYING)
            emit_signal(self, "status-changed")

    def pause(self):
        """
            Change player state to PAUSED
        """
        if isinstance(App().player.current_track, Radio):
            self._playbin.set_state(Gst.State.NULL)
        else:
            self._playbin.set_state(Gst.State.PAUSED)
        emit_signal(self, "status-changed")

    def stop(self, force=False):
        """
            Change player state to STOPPED
            @param force as bool
        """
        self._current_track = Track()
        self._playbin.set_state(Gst.State.NULL)
        emit_signal(self, "status-changed")
        emit_signal(self, "current-changed")
        if force:
            self._prev_track = Track()
            self._next_track = Track()
            emit_signal(self, "prev-changed")
            emit_signal(self, "next-changed")
            self.clear_albums()

    def stop_all(self):
        """
            Stop all bins, lollypop should quit now
        """
        # Stop
        self.__playbin1.set_state(Gst.State.NULL)
        self.__playbin2.set_state(Gst.State.NULL)

    def play_pause(self):
        """
            Set playing if paused
            Set paused if playing
        """
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def reload_track(self):
        """
            Reload track at current position
        """
        if self.current_track.id is None:
            return
        position = self.position
        self.__load(self.current_track)
        GLib.timeout_add(100, self.seek, position / Gst.SECOND)

    def seek(self, position):
        """
            Seek current track to position
            @param position as seconds
        """
        if self._current_track.id is None:
            return
        # Seems gstreamer doesn't like seeking to end, sometimes
        # doesn't go to next track
        if position >= self._current_track.duration:
            self.next()
        else:
            self._playbin.seek_simple(Gst.Format.TIME,
                                      Gst.SeekFlags.FLUSH |
                                      Gst.SeekFlags.KEY_UNIT,
                                      position * Gst.SECOND)
            emit_signal(self, "seeked", position)

    @property
    def plugins(self):
        """
            Get plugins
            @return [PluginsPlayer]
        """
        return [self._plugins1, self._plugins2]

    @property
    def is_playing(self):
        """
            True if player is playing
            @return bool
        """
        ok, state, pending = self._playbin.get_state(Gst.CLOCK_TIME_NONE)
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    @property
    def position(self):
        """
            Return bin playback position
            @HACK handle crossefade here, as we know we're going to be
            called every seconds
            @return position in Gst.SECOND
        """
        position = self._playbin.query_position(Gst.Format.TIME)[1]
        if self._crossfading and self._current_track.duration > 0:
            duration = self._current_track.duration - position / Gst.SECOND
            if duration < App().settings.get_value(
                    "transition-duration").get_int32():
                self.__do_crossfade(duration)
        return position

    @property
    def current_track(self):
        """
            Current track
        """
        return self._current_track

    @property
    def volume(self):
        """
            Return player volume rate
            @return rate as double
        """
        return self._playbin.get_volume(GstAudio.StreamVolumeFormat.CUBIC)

    def set_volume(self, rate):
        """
            Set player volume rate
            @param rate as double
        """
        if rate < 0.0:
            rate = 0.0
        elif rate > 1.0:
            rate = 1.0
        self.__playbin1.set_volume(GstAudio.StreamVolumeFormat.CUBIC, rate)
        self.__playbin2.set_volume(GstAudio.StreamVolumeFormat.CUBIC, rate)

    def next(self):
        """
            Go next track
        """
        pass

#######################
# PROTECTED           #
#######################
    def _load_track(self, track, init_volume=True):
        """
            Load track
            @param track as Track
            @param init volume as bool
            @return False if track not loaded
        """
        if init_volume:
            self._plugins.volume.props.volume = 1.0
        Logger.debug("BinPlayer::_load_track(): %s" % track.uri)
        try:
            self.__cancellable.cancel()
            self.__cancellable = Gio.Cancellable()
            if self._current_track.is_web:
                emit_signal(self, "loading-changed", False, track)
            self._current_track = track
            # We check track is URI track, if yes, do a load from Web
            # Will not work if we add another music provider one day
            track_uri = App().tracks.get_uri(track.id)
            if track.is_web and track.uri == track_uri:
                emit_signal(self, "loading-changed", True, track)
                App().task_helper.run(self._load_from_web, track)
                return False
            else:
                self._playbin.set_property("uri", track.uri)
        except Exception as e:  # Gstreamer error
            Logger.error("BinPlayer::_load_track(): %s" % e)
            return False
        return True

    def _load_from_web(self, track, play=True):
        """
            Load track from web
            @param track as Track
            @param play as bool
        """
        def play_uri(uri):
            track.set_uri(uri)
            if play:
                self.load(track)
                App().task_helper.run(self.__update_current_duration,
                                      track, uri)

        if get_network_available():
            from lollypop.helper_web import WebHelper
            helper = WebHelper()
            helper.set_uri(track, self.__cancellable)
            uri = helper.get_track_content(track)
            if uri is not None:
                GLib.idle_add(play_uri, uri)
            elif play:
                self.next()
        elif play:
            self.skip_album()

    def _scrobble(self, finished, finished_start_time):
        """
            Scrobble on lastfm
            @param finished as Track
            @param finished_start_time as int
        """
        played = time() - finished_start_time
        # Last.fm policy, force it for ListenBrainz too
        if finished.duration < 30:
            return
        # We can listen if the track has been played
        # for at least half its duration, or for 4 minutes
        if played >= finished.duration / 2 or played >= 240:
            for scrobbler in App().scrobblers:
                if scrobbler.available:
                    scrobbler.listen(finished, int(finished_start_time))

    def _on_stream_start(self, bus, message):
        """
            On stream start
            Handle stream start: scrobbling, notify, ...
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        if self._current_track.is_web:
            emit_signal(self, "loading-changed", False,
                        self._current_track.album)
        self._start_time = time()
        Logger.debug("Player::_on_stream_start(): %s" %
                     self._current_track.uri)
        emit_signal(self, "current-changed")
        for scrobbler in App().scrobblers:
            if scrobbler.available:
                scrobbler.playing_now(self._current_track)
        App().tracks.set_listened_at(self._current_track.id, int(time()))

    def _on_bus_message_tag(self, bus, message):
        """
            Read tags from stream
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        if isinstance(self._current_track, Track):
            return
        Logger.debug("Player::__on_bus_message_tag(): %s" %
                     self._current_track.uri)
        reader = TagReader()
        tags = message.parse_tag()
        title = reader.get_title(tags, "")
        if len(title) > 1 and self._current_track.artists != [title]:
            self._current_track.artists = [title]
            emit_signal(self, "current-changed")

    def _on_bus_element(self, bus, message):
        """
            Set elements for missings plugins
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        if GstPbutils.is_missing_plugin_message(message):
            self.__codecs.append(message)

    def _on_bus_error(self, bus, message):
        """
            Try a codec install and update current track
            @param bus as Gst.Bus
            @param message as Gst.Message
        """
        if self._current_track.is_web:
            emit_signal(self, "loading-changed", False,
                        self._current_track.album)
        Logger.info("Player::_on_bus_error(): %s" % message.parse_error()[1])
        if self.current_track.id is not None and self.current_track.id >= 0:
            if self.__codecs.is_missing_codec(message):
                self.__codecs.install()
                App().scanner.stop()
                self.stop()
            else:
                (error, parsed) = message.parse_error()
                App().notify.send(parsed)
                self.stop()

    def _on_bus_eos(self, bus, message):
        """
            Continue playback if possible and wanted
            go next otherwise
        """
        # Don't do anything if crossfade on, track already changed
        if self._crossfading:
            return
        if isinstance(App().player.current_track, Radio):
            return
        if self.is_playing and self._playbin.get_bus() == bus:
            if self._next_track.id is None:
                # We are in gstreamer thread
                GLib.idle_add(self.stop)
                # Reenable as it has been disabled by do_crossfading()
                self.update_crossfading()
            else:
                self._load_track(self._next_track)
                self.next()

    def _on_stream_about_to_finish(self, playbin):
        """
            When stream is about to finish, switch to next track without gap
            @param playbin as Gst.Bin
        """
        Logger.debug("Player::__on_stream_about_to_finish(): %s" % playbin)
        # Don't do anything if crossfade on, track already changed
        if self._crossfading:
            return
        if isinstance(App().player.current_track, Radio):
            return
        self._scrobble(self._current_track, self._start_time)
        # Increment popularity
        if self._current_track.id is not None and self._current_track.id >= 0:
            App().tracks.set_more_popular(self._current_track.id)
            # In party mode, linear popularity
            if self.is_party:
                pop_to_add = 1
            # In normal mode, based on tracks count
            else:
                count = self._current_track.album.tracks_count
                pop_to_add = int(App().albums.max_count / count)
            App().albums.set_more_popular(self._current_track.album_id,
                                          pop_to_add)
        if self._next_track.id is None:
            # We are in gstreamer thread
            GLib.idle_add(self.stop)
            # Reenable as it has been disabled by do_crossfading()
            self.update_crossfading()
        else:
            self._load_track(self._next_track)

#######################
# PRIVATE             #
#######################
    def __load(self, track, init_volume=True):
        """
            Stop current track, load track id and play it
            If was playing, do not use play as status doesn"t changed
            @param track as Track
            @param init volume as bool
        """
        was_playing = self.is_playing
        self._playbin.set_state(Gst.State.NULL)
        if self._load_track(track, init_volume):
            if was_playing:
                self._playbin.set_state(Gst.State.PLAYING)
            else:
                self.play()

    def __volume_up(self, playbin, plugins, duration):
        """
            Make volume going up smoothly
            @param playbin as Gst.Bin
            @param plugins as PluginsPlayer
            @param duration as int
        """
        # We are not the active playbin, stop all
        if self._playbin != playbin:
            return
        if duration > 0:
            vol = plugins.volume.props.volume
            steps = duration / 0.25
            vol_up = (1.0 - vol) / steps
            rate = vol + vol_up
            if rate < 1.0:
                plugins.volume.props.volume = rate
                GLib.timeout_add(250, self.__volume_up,
                                 playbin, plugins, duration - 0.25)
            else:
                plugins.volume.props.volume = 1.0
        else:
            plugins.volume.props.volume = 1.0

    def __volume_down(self, playbin, plugins, duration):
        """
            Make volume going down smoothly
            @param playbin as Gst.Bin
            @param plugins as PluginsPlayer
            @param duration as int
        """
        # We are again the active playbin, stop all
        if self._playbin == playbin:
            return
        if duration > 0:
            vol = plugins.volume.props.volume
            steps = duration / 0.25
            vol_down = vol / steps
            rate = vol - vol_down
            if rate > 0:
                plugins.volume.props.volume = rate
                GLib.timeout_add(250, self.__volume_down,
                                 playbin, plugins, duration - 0.25)
            else:
                plugins.volume.props.volume = 0.0
                playbin.set_state(Gst.State.NULL)
        else:
            plugins.volume.props.volume = 0.0
            playbin.set_state(Gst.State.NULL)

    def __do_crossfade(self, duration, track=None):
        """
            Crossfade tracks
            @param duration as int
            @param track as Track
        """
        if track is None:
            self._scrobble(self._current_track, self._start_time)
            # Increment popularity
            App().tracks.set_more_popular(self._current_track.id)
            # In party mode, linear popularity
            if self.is_party:
                pop_to_add = 1
            # In normal mode, based on tracks count
            else:
                count = self._current_track.album.tracks_count
                pop_to_add = int(App().albums.max_count / count)
            App().albums.set_more_popular(self._current_track.album_id,
                                          pop_to_add)

        GLib.idle_add(self.__volume_down, self._playbin,
                      self._plugins, duration)
        if self._playbin == self.__playbin2:
            self._playbin = self.__playbin1
            self._plugins = self._plugins1
        else:
            self._playbin = self.__playbin2
            self._plugins = self._plugins2

        if track is not None and track.id is not None:
            self.__load(track, False)
            self._plugins.volume.props.volume = 0
            GLib.idle_add(self.__volume_up, self._playbin,
                          self._plugins, duration)
        elif self._next_track.id is not None:
            self.__load(self._next_track, False)
            self._plugins.volume.props.volume = 0
            GLib.idle_add(self.__volume_up, self._playbin,
                          self._plugins, duration)

    def __update_current_duration(self, track, uri):
        """
            Update current track duration
            @param track as Track
            @param uri as str
        """
        try:
            discoverer = Discoverer()
            duration = discoverer.get_info(uri).get_duration() / 1000000000
            if duration != track.duration and duration > 0:
                App().tracks.set_duration(track.id, int(duration))
                track.reset("duration")
                emit_signal(self, "duration-changed", track.id)
        except Exception as e:
            Logger.error("BinPlayer::__update_current_duration(): %s" % e)

    def __on_volume_changed(self, playbin, sink):
        """
            Update volume
            @param playbin as Gst.Bin
            @param sink as Gst.Sink
        """
        if playbin == self.__playbin1:
            vol = self.__playbin1.get_volume(GstAudio.StreamVolumeFormat.CUBIC)
            self.__playbin2.set_volume(GstAudio.StreamVolumeFormat.CUBIC, vol)
        else:
            vol = self.__playbin2.get_volume(GstAudio.StreamVolumeFormat.CUBIC)
            self.__playbin1.set_volume(GstAudio.StreamVolumeFormat.CUBIC, vol)
        emit_signal(self, "volume-changed")
