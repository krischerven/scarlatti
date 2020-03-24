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

from lollypop.utils_album import tracks_to_albums
from lollypop.utils import get_default_storage_type
from lollypop.view_lazyloading import LazyLoadingView
from lollypop.define import App, ViewType, MARGIN, Type, Size, StorageType
from lollypop.objects_album import Album
from lollypop.objects_track import Track
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.widgets_banner_playlist import PlaylistBannerWidget
from lollypop.view_albums_list import AlbumsListView
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.helper_size_allocation import SizeAllocationHelper


class PlaylistsView(LazyLoadingView, ViewController,
                    SignalsHelper, SizeAllocationHelper):
    """
        View showing playlists
    """

    @signals_map
    def __init__(self, playlist_id, view_type):
        """
            Init PlaylistView
            @parma playlist_id as int
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, StorageType.ALL,
                                 view_type |
                                 ViewType.SCROLLED |
                                 ViewType.OVERLAY)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        SizeAllocationHelper.__init__(self)
        self._playlist_id = playlist_id
        # We remove SCROLLED because we want to be the scrolled view
        self._view = AlbumsListView([], [], view_type & ~ViewType.SCROLLED)
        self._view.set_width(Size.MEDIUM)
        if view_type & ViewType.DND:
            self._view.dnd_helper.connect("dnd-finished",
                                          self.__on_dnd_finished)
        self._view.show()
        self._banner = PlaylistBannerWidget(playlist_id, self._view)
        self._banner.show()
        self.add_widget(self._view, self._banner)
        return [
                (App().playlists, "playlist-track-added",
                 "_on_playlist_track_added"),
                (App().playlists, "playlist-track-removed",
                 "_on_playlist_track_removed"),
                (App().playlists, "playlists-changed", "_on_playlist_changed")
        ]

    def populate(self):
        """
            Populate view
        """
        def on_load(albums):
            self._view.add_reveal_albums(albums)
            self._view.populate(albums)

        def load():
            track_ids = []
            if self._playlist_id == Type.LOVED:
                for track_id in App().tracks.get_loved_track_ids(
                        self.storage_type):
                    if track_id not in track_ids:
                        track_ids.append(track_id)
            else:
                for track_id in App().playlists.get_track_ids(
                        self._playlist_id):
                    if track_id not in track_ids:
                        track_ids.append(track_id)
            return tracks_to_albums(
                [Track(track_id) for track_id in track_ids])

        App().task_helper.run(load, callback=(on_load,))

    def pause(self):
        """
            pause populating
        """
        self._view.pause()

    def remove_from_playlist(self, object):
        """
            Remove object from playlist
            @param object as Album/Track
        """
        if isinstance(object, Album):
            tracks = object.tracks
        else:
            tracks = [object]
        App().playlists.remove_tracks(self._playlist_id, tracks)

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"playlist_id": self._playlist_id,
                "view_type": self.view_type}

    @property
    def filtered(self):
        """
            Get filtered children
            @return [Gtk.Widget]
        """
        filtered = []
        for child in self._view.children:
            filtered.append(child)
            for subchild in child.children:
                filtered.append(subchild)
        return filtered

    @property
    def scroll_shift(self):
        """
            Get scroll shift for y axes
            @return int
        """
        return self._banner.height + MARGIN

    @property
    def scroll_relative_to(self):
        """
            Relative to scrolled widget
            @return Gtk.Widget
        """
        return self._view

#######################
# PROTECTED           #
#######################
    def _on_playlist_track_added(self, playlists, playlist_id, uri):
        """
            Append track to album list
            @param playlists as Playlists
            @param playlist_id as int
            @param uri as str
        """
        if playlist_id == self._playlist_id:
            track = Track(App().tracks.get_id_by_uri(uri))
            album = Album(track.album.id)
            album.set_tracks([track])
            self._view.add_reveal_albums([album])
            self._view.insert_album(album, -1)

    def _on_playlist_track_removed(self, playlists, playlist_id, uri):
        """
            Remove track from album list
            @param playlists as Playlists
            @param playlist_id as int
            @param uri as str
        """
        if playlist_id == self._playlist_id:
            track = Track(App().tracks.get_id_by_uri(uri))
            children = self._view.children
            for album_row in children:
                if album_row.album.id == track.album.id:
                    for track_row in album_row.children:
                        if track_row.track.id == track.id:
                            track_row.destroy()
                            if len(children) == 1:
                                album_row.destroy()
                                break

    def _on_playlist_changed(self, playlists, playlist_id):
        """
            Update playlist
            @param playlists as Playlists
            @param playlist_id as int
        """
        if playlist_id == self._playlist_id:
            # Playlist has been removed
            if not playlists.exists(playlist_id):
                App().window.container.go_back()
            else:
                self._view.clear()
                self.populate()

#######################
# PRIVATE             #
#######################
    def __on_dnd_finished(self, dnd_helper):
        """
            Save playlist if needed
            @param dnd_helper as DNDHelper
        """
        if self._playlist_id >= 0:
            uris = []
            for child in self._view.children:
                for track in child.album.tracks:
                    uris.append(track.uri)
            App().playlists.clear(self._playlist_id)
            App().playlists.add_uris(self._playlist_id, uris)


class SmartPlaylistsView(PlaylistsView):
    """
        View showing smart playlists
    """

    def __init__(self, playlist_id, view_type):
        """
            Init PlaylistView
            @parma playlist_id as int
            @param view_type as ViewType
        """
        PlaylistsView.__init__(self, playlist_id, view_type)

    def populate(self):
        """
            Populate view
        """
        def on_load(albums):
            self._banner.spinner.stop()
            self._view.add_reveal_albums(albums)
            self._view.populate(albums)

        def load():
            request = App().playlists.get_smart_sql(self._playlist_id)
            # We need to inject storage_type
            storage_type = get_default_storage_type()
            split = request.split("ORDER BY")
            split[0] += " AND tracks.storage_type&%s " % storage_type
            track_ids = App().db.execute("ORDER BY".join(split))
            return tracks_to_albums(
                [Track(track_id) for track_id in track_ids])

        self._banner.spinner.start()
        App().task_helper.run(load, callback=(on_load,))
