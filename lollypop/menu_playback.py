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

from gi.repository import Gio, GLib

from gettext import gettext as _

from lollypop.define import App
from lollypop.utils import tracks_to_albums, emit_signal
from lollypop.objects_track import Track
from lollypop.objects_album import Album


class BasePlaybackMenu(Gio.Menu):
    """
        Base class for playback menu
    """

    def __init__(self):
        """
            Init menu
        """
        Gio.Menu.__init__(self)

    @property
    def in_player(self):
        """
            True if current object in player
            return bool
        """
        return False

#######################
# PROTECTED           #
#######################
    def _set_playback_actions(self):
        """
            Setup playback actions
        """
        if not self.in_player:
            append_playback_action = Gio.SimpleAction(
                name="append_playback_action")
            App().add_action(append_playback_action)
            append_playback_action.connect("activate",
                                           self._append_to_playback)
            menu_item = Gio.MenuItem.new(_("Add to playback"),
                                         "app.append_playback_action")
        else:
            del_playback_action = Gio.SimpleAction(name="del_playback_action")
            App().add_action(del_playback_action)
            del_playback_action.connect("activate",
                                        self._remove_from_playback)
            menu_item = Gio.MenuItem.new(_("Remove from playback"),
                                         "app.del_playback_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)


class PlaylistPlaybackMenu(Gio.Menu):
    """
        Contextual menu for a playlist
    """

    def __init__(self, playlist_id):
        """
            Init menu
            @param playlist id as int
        """
        Gio.Menu.__init__(self)
        play_action = Gio.SimpleAction(name="playlist_play_action")
        App().add_action(play_action)
        play_action.connect("activate", self.__play, playlist_id)
        menu_item = Gio.MenuItem.new(_("Play this playlist"),
                                     "app.playlist_play_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)

#######################
# PRIVATE             #
#######################
    def __play(self, action, variant, playlist_id):
        """
            Play albums
            @param Gio.SimpleAction
            @param GLib.Variant
            @param playlist_id as int
        """
        if App().playlists.get_smart(playlist_id):
            tracks = []
            request = App().playlists.get_smart_sql(playlist_id)
            for track_id in App().db.execute(request):
                tracks.append(Track(track_id))
        else:
            tracks = App().playlists.get_tracks(playlist_id)
        albums = tracks_to_albums(tracks)
        App().player.play_albums(albums)


class ArtistPlaybackMenu(BasePlaybackMenu):
    """
        Contextual menu for an artist
    """

    def __init__(self, artist_id):
        """
            Init menu
            @param artist id as int
        """
        BasePlaybackMenu.__init__(self)
        self.__artist_id = artist_id
        play_action = Gio.SimpleAction(name="artist_play_action")
        App().add_action(play_action)
        play_action.connect("activate", self.__play)
        menu_item = Gio.MenuItem.new(_("Play this artist"),
                                     "app.artist_play_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)
        self._set_playback_actions()

    @property
    def in_player(self):
        """
            True if current object in player
            return bool
        """
        album_ids = App().albums.get_ids([self.__artist_id], [])
        return set(App().player.album_ids) & set(album_ids) == set(album_ids)

#######################
# PROTECTED           #
#######################
    def _append_to_playback(self, action, variant):
        """
            Append track to playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        from lollypop.utils_artist import add_artist_to_playback
        add_artist_to_playback([self.__artist_id], (), True)

    def _remove_from_playback(self, action, variant):
        """
            Delete track id from playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        from lollypop.utils_artist import add_artist_to_playback
        add_artist_to_playback([self.__artist_id], (), False)

#######################
# PRIVATE             #
#######################
    def __play(self, action, variant):
        """
            Play albums
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        from lollypop.utils_artist import play_artists
        play_artists([self.__artist_id], [])


class GenrePlaybackMenu(BasePlaybackMenu):
    """
        Contextual menu for a genre
    """

    def __init__(self, genre_id):
        """
            Init decade menu
            @param genre_id as int
        """
        BasePlaybackMenu.__init__(self)
        self.__genre_id = genre_id
        play_action = Gio.SimpleAction(name="genre_play_action")
        App().add_action(play_action)
        play_action.connect("activate", self.__play)
        menu_item = Gio.MenuItem.new(_("Play this genre"),
                                     "app.genre_play_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)
        self._set_playback_actions()

    @property
    def in_player(self):
        """
            True if current object in player
            return bool
        """
        album_ids = self.__get_album_ids()
        return set(App().player.album_ids) & set(album_ids) == set(album_ids)

#######################
# PROTECTED           #
#######################
    def _append_to_playback(self, action, variant):
        """
            Append track to playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        album_ids = self.__get_album_ids()
        for album_id in album_ids:
            album = Album(album_id)
            App().player.add_album(album)
        App().player.update_next_prev()

    def _remove_from_playback(self, action, variant):
        """
            Delete track id from playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        album_ids = self.__get_album_ids()
        for album_id in album_ids:
            App().player.remove_album_by_id(album_id)
        App().player.update_next_prev()

#######################
# PRIVATE             #
#######################
    def __get_album_ids(self):
        """
            Get album ids for genre
            @return [int]
        """
        album_ids = App().albums.get_compilation_ids([self.__genre_id], True)
        album_ids += App().albums.get_ids([], [self.__genre_id], True)
        return album_ids

    def __play(self, action, variant):
        """
            Play albums
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        album_ids = self.__get_album_ids()
        albums = [Album(album_id) for album_id in album_ids]
        App().player.play_albums(albums)


class DecadePlaybackMenu(BasePlaybackMenu):
    """
        Contextual menu for a decade
    """

    def __init__(self, years):
        """
            Init decade menu
            @param years as [int]
        """
        BasePlaybackMenu.__init__(self)
        self.__years = years
        play_action = Gio.SimpleAction(name="decade_play_action")
        App().add_action(play_action)
        play_action.connect("activate", self.__play)
        menu_item = Gio.MenuItem.new(_("Play this decade"),
                                     "app.decade_play_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)
        self._set_playback_actions()

    @property
    def in_player(self):
        """
            True if current object in player
            return bool
        """
        album_ids = self.__get_album_ids()
        return set(App().player.album_ids) & set(album_ids) == set(album_ids)

#######################
# PROTECTED           #
#######################
    def _append_to_playback(self, action, variant):
        """
            Append track to playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        album_ids = self.__get_album_ids()
        for album_id in album_ids:
            album = Album(album_id)
            App().player.add_album(album)
        App().player.update_next_prev()

    def _remove_from_playback(self, action, variant):
        """
            Delete track id from playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        album_ids = self.__get_album_ids()
        for album_id in album_ids:
            App().player.remove_album_by_id(album_id)
        App().player.update_next_prev()

#######################
# PRIVATE             #
#######################
    def __get_album_ids(self):
        """
            Get album ids for decade
            @return [int]
        """
        album_ids = []
        for year in self.__years:
            album_ids += App().albums.get_compilations_for_year(year)
            album_ids += App().albums.get_albums_for_year(year)
        return album_ids

    def __play(self, action, variant):
        """
            Play albums
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        album_ids = self.__get_album_ids()
        albums = [Album(album_id) for album_id in album_ids]
        App().player.play_albums(albums)


class AlbumPlaybackMenu(BasePlaybackMenu):
    """
        Contextual menu for an album
    """

    def __init__(self, album):
        """
            Init album menu
            @param album as Album
        """
        BasePlaybackMenu.__init__(self)
        self.__album = album
        play_action = Gio.SimpleAction(name="album_play_action")
        App().add_action(play_action)
        play_action.connect("activate", self.__play)
        menu_item = Gio.MenuItem.new(_("Play this album"),
                                     "app.album_play_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)
        self._set_playback_actions()

    @property
    def in_player(self):
        """
            True if current object in player
            return bool
        """
        return self.__album.id in App().player.album_ids

#######################
# PROTECTED           #
#######################
    def _append_to_playback(self, action, variant):
        """
            Append track to playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.add_album(self.__album)
        App().player.update_next_prev()

    def _remove_from_playback(self, action, variant):
        """
            Delete track id from playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.remove_album_by_id(self.__album.id)
        App().player.update_next_prev()

#######################
# PRIVATE             #
#######################
    def __play(self, action, variant):
        """
            Play album
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.play_album(self.__album)


class TrackPlaybackMenu(BasePlaybackMenu):
    """
        Contextual menu for tracks
    """

    def __init__(self, track):
        """
            Init track menu
            @param track as Track
        """
        BasePlaybackMenu.__init__(self)
        self.__track = track
        self._set_playback_actions()
        self.__set_queue_actions()
        self.__set_stop_after_action()

    @property
    def in_player(self):
        """
            True if current object in player
            return bool
        """
        for album in App().player.albums:
            if self.__track.album.id == album.id:
                if self.__track.id in album.track_ids:
                    return True
        return False

#######################
# PROTECTED           #
#######################
    def _append_to_playback(self, action, variant):
        """
            Append track to playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        albums = App().player.albums
        # If album last in list, merge
        if albums and albums[-1].id == self.__track.album.id:
            albums[-1].append_track(self.__track)
            App().player.set_next()
        # Add album with only one track
        else:
            album = Album(self.__track.album.id)
            album.set_tracks([self.__track])
            if App().player.is_playing:
                App().player.add_album(album)
            else:
                App().player.play_album(album)

    def _remove_from_playback(self, action, variant):
        """
            Delete track id from playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        for album in App().player.albums:
            if album.id == self.__track.album.id:
                if self.__track.id in album.track_ids:
                    index = album.track_ids.index(self.__track.id)
                    track = album.tracks[index]
                    album.remove_track(track)
                    break
        App().player.set_next()
        App().player.set_prev()

#######################
# PRIVATE             #
#######################
    def __set_queue_actions(self):
        """
            Set queue actions
        """
        if self.__track.id not in App().player.queue:
            append_queue_action = Gio.SimpleAction(name="append_queue_action")
            App().add_action(append_queue_action)
            append_queue_action.connect("activate",
                                        self.__append_to_queue)
            self.append(_("Add to queue"), "app.append_queue_action")
        else:
            del_queue_action = Gio.SimpleAction(name="del_queue_action")
            App().add_action(del_queue_action)
            del_queue_action.connect("activate",
                                     self.__remove_from_queue)
            self.append(_("Remove from queue"), "app.del_queue_action")

    def __set_stop_after_action(self):
        """
            Add an action to stop playback after track
        """
        if self.in_player and isinstance(self.__track, Track):
            stop_after_action = Gio.SimpleAction(name="stop_after_action")
            App().add_action(stop_after_action)
            if self.__track.id == App().player.stop_after_track_id:
                stop_after_action.connect("activate", self.__stop_after, None)
                self.append(_("Do not stop after"),
                            "app.stop_after_action")
            else:
                stop_after_action.connect("activate", self.__stop_after,
                                          self.__track.id)
                self.append(_("Stop after"), "app.stop_after_action")

    def __stop_after(self, action, variant, track_id):
        """
            Tell player to stop after track
            @param Gio.SimpleAction
            @param GLib.Variant
            @param track_id as int/None
        """
        App().player.stop_after(track_id)
        if track_id == App().player.current_track.id:
            App().player.set_next()

    def __append_to_queue(self, action, variant):
        """
            Append track to queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.append_to_queue(self.__track.id, False)
        emit_signal(App().player, "queue-changed")

    def __remove_from_queue(self, action, variant):
        """
            Delete track id from queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.remove_from_queue(self.__track.id, False)
        emit_signal(App().player, "queue-changed")
