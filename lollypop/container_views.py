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

from lollypop.shown import ShownLists
from lollypop.loader import Loader
from lollypop.objects import Track, Album
from lollypop.define import App, Type, ViewType, SelectionListMask
from lollypop.define import MARGIN_SMALL
from lollypop.define import SidebarContent


class ViewsContainer:
    """
        Views management for main view
    """

    def __init__(self):
        """
            Init container
        """
        pass

    def show_lyrics(self, track=None):
        """
            Show lyrics for track
            @pram track as Track
        """
        if track is None and App().player.current_track.id is None:
            return
        from lollypop.view_lyrics import LyricsView
        current = self._stack.get_visible_child()
        view = LyricsView()
        view.populate(track or App().player.current_track)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        current.disable_overlay()

    def show_view(self, item_ids, data=None, switch=True):
        """
            Show view for item id
            @param item_ids as [int]
            @param data as object
            @param switch as bool
        """
        App().window.emit("can-go-back-changed", True)
        view = None
        if item_ids:
            if item_ids[0] in [Type.POPULARS,
                               Type.LOVED,
                               Type.RECENTS,
                               Type.NEVER,
                               Type.RANDOMS,
                               Type.WEB]:
                view = self._get_view_albums(item_ids, [])
            elif item_ids[0] == Type.SEARCH:
                view = self.get_view_search(data)
            elif item_ids[0] == Type.INFO:
                view = self._get_view_info()
            elif item_ids[0] == Type.DEVICE_ALBUMS:
                view = self._get_view_device_albums(data)
            elif item_ids[0] == Type.DEVICE_PLAYLISTS:
                view = self._get_view_device_playlists(data)
            elif item_ids[0] == Type.GENRES:
                if data is None:
                    view = self._get_view_genres()
                else:
                    view = self._get_view_albums([data], [])
            elif item_ids[0] == Type.ALBUM:
                view = self._get_view_album(data)
            elif item_ids[0] == Type.YEARS:
                if data is None:
                    view = self._get_view_albums_decades()
                else:
                    view = self._get_view_albums_years(data)
            elif item_ids[0] == Type.PLAYLISTS:
                view = self._get_view_playlists([] if data is None else data)
            elif item_ids[0] == Type.RADIOS:
                view = self._get_view_radios()
            elif item_ids[0] == Type.EQUALIZER:
                from lollypop.view_equalizer import EqualizerView
                view = EqualizerView()
            elif item_ids[0] in [Type.SETTINGS,
                                 Type.SETTINGS_APPEARANCE,
                                 Type.SETTINGS_BEHAVIOUR,
                                 Type.SETTINGS_COLLECTIONS,
                                 Type.SETTINGS_WEB,
                                 Type.SETTINGS_DEVICES]:
                view = self._get_view_settings(item_ids[0])
            elif item_ids[0] == Type.ALL:
                view = self._get_view_albums(item_ids, [])
            elif item_ids[0] == Type.COMPILATIONS:
                view = self._get_view_albums([], item_ids)
            elif item_ids[0] == Type.ARTISTS:
                # Here we handle static items for RoundedArtistView
                if data and data[0] < 0:
                    self.show_view(data)
                    return
                elif data is None:
                    view = self._rounded_artists_view
        if view is None:
            view = self._get_view_artists(item_ids, data)
        view.show()
        self._stack.add(view)
        if switch:
            self._stack.set_visible_child(view)

    def get_view_current(self, view_type=ViewType.DND):
        """
            Get view for current playlist
            @return View
        """
        if App().player.queue and not view_type & ViewType.FULLSCREEN:
            from lollypop.view_queue import QueueView
            view = QueueView(view_type | self._view_type)
            view.populate()
        elif App().player.playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(App().player.playlist_ids,
                                 view_type | self._view_type)
            view.populate(App().player.playlist_tracks)
        else:
            from lollypop.view_current_albums import CurrentAlbumsView
            view = CurrentAlbumsView(view_type | self._view_type)
            view.populate(App().player.albums)
        view.set_margin_top(MARGIN_SMALL)
        view.set_margin_start(MARGIN_SMALL)
        view.show()
        return view

    def get_view_search(self, search=""):
        """
            Get view for search
            @param search as str
            @return SearchView
        """
        from lollypop.view_search import SearchView
        # Search view in children
        for child in self._stack.get_children():
            if isinstance(child, SearchView):
                child.set_search(search)
                return child
        view = SearchView()
        view.set_margin_top(MARGIN_SMALL)
        view.set_margin_start(MARGIN_SMALL)
        view.set_search(search)
        view.show()
        return view

    def get_view_album_ids(self, genre_ids, artist_ids):
        """
            Get albums view for genres/artists
            @param genre_ids as [int]
            @param artist_ids as [int]
            @return [int]
        """
        items = []
        is_compilation = artist_ids and artist_ids[0] == Type.COMPILATIONS
        if genre_ids and genre_ids[0] == Type.ALL:
            if is_compilation or\
                    App().settings.get_value(
                        "show-compilations-in-album-view"):
                items = App().albums.get_compilation_ids([])
            if not is_compilation:
                items += App().albums.get_ids([], [])
        elif genre_ids and genre_ids[0] == Type.POPULARS:
            items = App().albums.get_rated()
            count = 100 - len(items)
            for album in App().albums.get_populars(count):
                if album not in items:
                    items.append(album)
        elif genre_ids and genre_ids[0] == Type.LOVED:
            items = App().albums.get_loved_albums()
        elif genre_ids and genre_ids[0] == Type.RECENTS:
            items = App().albums.get_recents()
        elif genre_ids and genre_ids[0] == Type.NEVER:
            items = App().albums.get_never_listened_to()
        elif genre_ids and genre_ids[0] == Type.RANDOMS:
            items = App().albums.get_randoms()
        else:
            if is_compilation or\
                    App().settings.get_value(
                        "show-compilations-in-album-view"):
                items = App().albums.get_compilation_ids(genre_ids)
            if not is_compilation:
                items += App().albums.get_ids([], genre_ids)
        return items

    def show_artist_view(self, artist_ids):
        """
            Go to artist view
            @param artist_ids as [int]
        """
        if App().settings.get_value("show-sidebar") and\
                not App().window.is_adaptive:
            App().window.container.show_artists_albums(artist_ids)
        else:
            App().window.container.show_view(artist_ids)

##############
# PROTECTED  #
##############
    def _get_view_playlists(self, playlist_ids=[]):
        """
            Get playlists view for playlists
            @param playlist_ids as [int]
            @return View
        """
        def load():
            tracks = []
            all_ids = []
            for playlist_id in playlist_ids:
                if playlist_id == Type.LOVED:
                    ids = App().tracks.get_loved_track_ids()
                else:
                    ids = App().playlists.get_track_ids(playlist_id)
                for id in ids:
                    if id in all_ids:
                        continue
                    all_ids.append(id)
                    track = Track(id)
                    tracks.append(track)
            return tracks

        def load_smart():
            tracks = []
            request = App().playlists.get_smart_sql(playlist_ids[0])
            ids = App().db.execute(request)
            for id in ids:
                track = Track(id)
                # Smart playlist may report invalid tracks
                # An album always have an artist so check
                # object is valid. Others Lollypop widgets assume
                # objects are valid
                if not track.album.artist_ids:
                    continue
                tracks.append(track)
            return tracks

        if App().window.is_adaptive:
            view_type = ViewType.DND
        else:
            view_type = ViewType.TWO_COLUMNS |\
                        ViewType.DND |\
                        ViewType.PLAYLISTS
        if len(playlist_ids) == 1 and\
                App().playlists.get_smart(playlist_ids[0]):
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(playlist_ids, view_type | self._view_type)
            view.show()
            loader = Loader(target=load_smart, view=view)
            loader.start()
        elif playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            view = PlaylistsView(playlist_ids, view_type | self._view_type)
            view.show()
            loader = Loader(target=load, view=view)
            loader.start()
        else:
            from lollypop.view_playlists_manager import PlaylistsManagerView
            view_type = ViewType.SCROLLED
            if App().window.is_adaptive:
                view_type |= ViewType.MEDIUM
            view = PlaylistsManagerView(None, view_type | self._view_type)
            view.populate()
            view.show()
        return view

    def _get_view_device_playlists(self, index):
        """
            Show playlists for device at index
            @param index as int
        """
        def load():
            playlist_ids = App().playlists.get_synced_ids(0)
            playlist_ids += App().playlists.get_synced_ids(index)
            return playlist_ids

        from lollypop.view_playlists_manager import PlaylistsManagerView
        view = PlaylistsManagerView(None, ViewType.SCROLLED | ViewType.DEVICES)
        view.show()
        loader = Loader(target=load, view=view)
        loader.start()
        return view

    def _get_view_artists_rounded(self, static):
        """
            Get rounded artists view
            @return view
        """
        def load():
            if App().settings.get_value("show-performers"):
                ids = App().artists.get_all()
            else:
                ids = App().artists.get()
            compilations = App().albums.get_compilation_ids([])
            return (ids, compilations)

        def get_items(artist_ids, compilation_ids):
            items = []
            if static:
                mask = SelectionListMask.ARTISTS_VIEW |\
                       SelectionListMask.ARTISTS
                if compilation_ids:
                    mask |= SelectionListMask.COMPILATIONS
                items = ShownLists.get(mask)
            items += artist_ids
            return items

        def setup(artist_ids, compilation_ids):
            view.populate(get_items(artist_ids, compilation_ids))

        from lollypop.view_artists_rounded import RoundedArtistsView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = RoundedArtistsView(view_type | self._view_type, not static)
        self._stack.add(view)
        loader = Loader(target=load, view=view,
                        on_finished=lambda r: setup(*r))
        loader.start()
        view.show()
        return view

    def _get_view_artists(self, genre_ids, artist_ids):
        """
            Get artists view for genres/artists
            @param genre_ids as [int]
            @param artist_ids as [int]
        """
        def load():
            if genre_ids and genre_ids[0] == Type.ALL:
                if App().settings.get_value("show-performers"):
                    items = App().tracks.get_album_ids(artist_ids, [])
                else:
                    items = App().albums.get_ids(artist_ids, [])
            else:
                if App().settings.get_value("show-performers"):
                    items = App().tracks.get_album_ids(artist_ids, genre_ids)
                else:
                    items = App().albums.get_ids(artist_ids, genre_ids)
            return [Album(album_id, genre_ids, artist_ids)
                    for album_id in items]
        if App().window.is_adaptive:
            from lollypop.view_artist_small import ArtistViewSmall
            view = ArtistViewSmall(artist_ids, genre_ids)
        else:
            from lollypop.view_artist import ArtistView
            view = ArtistView(artist_ids, genre_ids)
            loader = Loader(target=load, view=view)
            loader.start()
        view.show()
        return view

    def _get_view_albums_decades(self):
        """
            Get album view for decades
        """
        def load():
            (years, unknown) = App().albums.get_years()
            decades = []
            decade = []
            current_d = None
            for year in sorted(years):
                d = year // 10
                if current_d is not None and current_d != d:
                    current_d = d
                    decades.append(decade)
                    decade = []
                current_d = d
                decade.append(year)
            if decade:
                decades.append(decade)
            return decades
        from lollypop.view_albums_decade_box import AlbumsDecadeBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = AlbumsDecadeBoxView(self._view_type | view_type)
        view.show()
        loader = Loader(target=load, view=view)
        loader.start()
        return view

    def _get_view_album(self, album):
        """
            Show album
            @param album as Album
        """
        from lollypop.view_album import AlbumView
        view_type = ViewType.TWO_COLUMNS
        if App().window.is_adaptive:
            view_type |= ViewType.SMALL
        view = AlbumView(album, album.artist_ids, album.genre_ids,
                         view_type | self._view_type)
        view.populate()
        return view

    def _get_view_genres(self):
        """
            Get view for genres
        """
        def load():
            return App().genres.get_ids()

        from lollypop.view_albums_genre_box import AlbumsGenreBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = AlbumsGenreBoxView(view_type | self._view_type)
        view.show()
        loader = Loader(target=load, view=view)
        loader.start()
        return view

    def _get_view_albums_years(self, years):
        """
            Get album view for years
            @param years as [int]
        """
        def load():
            items = []
            for year in years:
                items += App().albums.get_compilations_for_year(year)
                items += App().albums.get_albums_for_year(year)
            return [Album(album_id, [Type.YEARS], [])
                    for album_id in items]
        from lollypop.view_albums_box import AlbumsBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = AlbumsBoxView([Type.YEARS], years, view_type | self._view_type)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def _get_view_albums(self, genre_ids, artist_ids):
        """
            Get albums view for genres/artists
            @param genre_ids as [int]
            @param is compilation as bool
        """
        def load():
            album_ids = self.get_view_album_ids(genre_ids, artist_ids)
            return [Album(album_id, genre_ids, artist_ids)
                    for album_id in album_ids]

        from lollypop.view_albums_box import AlbumsBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = AlbumsBoxView(genre_ids, artist_ids,
                             view_type | self._view_type)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def _get_view_device_albums(self, index):
        """
            Show albums for device at index
            @param index as int
        """
        def load():
            album_ids = App().albums.get_synced_ids(0)
            album_ids += App().albums.get_synced_ids(index)
            return [Album(album_id) for album_id in album_ids]

        from lollypop.view_albums_box import AlbumsBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = AlbumsBoxView([], [], view_type | self._view_type)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def _get_view_radios(self):
        """
            Get radios view
            @return RadiosView
        """
        def load():
            from lollypop.radios import Radios
            radios = Radios()
            return radios.get_ids()
        from lollypop.view_radios import RadiosView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = RadiosView(view_type | self._view_type)
        loader = Loader(target=load, view=view)
        loader.start()
        view.show()
        return view

    def _get_view_info(self):
        """
            Get view for information
            @return InformationView
        """
        from lollypop.view_information import InformationView
        view = InformationView(True)
        view.populate()
        view.set_margin_top(MARGIN_SMALL)
        view.set_margin_start(MARGIN_SMALL)
        view.show()
        return view

    def _get_view_settings(self, item_id):
        """
            Show settings views
            @param item_id as int
        """
        if item_id == Type.SETTINGS:
            from lollypop.view_settings import SettingsView
            view = SettingsView()
        else:
            from lollypop.view_settings import SettingsChildView
            view = SettingsChildView(item_id)
        return view

    def _restore_state(self):
        """
            Restore state
        """
        self._stack.destroy_children()
        state_one_ids = App().settings.get_value("state-one-ids")
        state_two_ids = App().settings.get_value("state-two-ids")
        state_three_ids = App().settings.get_value("state-three-ids")
        sidebar_content = App().settings.get_enum("sidebar-content")
        if state_one_ids and state_two_ids and state_three_ids:
            self.show_view(state_one_ids, None, False)
            album = Album(state_three_ids[0], state_one_ids, state_two_ids)
            self.show_view([Type.ALBUM], album)
        elif state_one_ids and state_two_ids:
            if sidebar_content == SidebarContent.GENRES:
                self.show_view([Type.GENRES], None, False)
                self.show_view([Type.GENRES], state_one_ids[0], False)
                self.show_view(state_two_ids)
            else:
                self.show_view(state_one_ids, None, False)
                self.show_view(state_one_ids, state_two_ids)
        elif state_one_ids:
            self.show_view(state_one_ids)

############
# PRIVATE  #
############
