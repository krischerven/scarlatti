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

from lollypop.define import App, Type, ViewType
from lollypop.define import MARGIN_SMALL


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
        self._list_view.hide()
        self._sidebar.select_ids([], False)
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
                view = self._get_view_artists([], data)
        if view is not None:
            view.show()
            self._stack.add(view)
            if switch:
                self._stack.set_visible_child(view)

    def get_view_current(self, view_type=ViewType.DND | ViewType.SCROLLED):
        """
            Get view for current playlist
            @return View
        """
        if App().player.queue and not view_type & ViewType.FULLSCREEN:
            from lollypop.view_queue import QueueView
            view = QueueView(view_type)
            view.populate()
        else:
            from lollypop.view_current_albums import CurrentAlbumsView
            view = CurrentAlbumsView(view_type)
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
        view = SearchView(ViewType.SEARCH | ViewType.SCROLLED)
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

##############
# PROTECTED  #
##############
    def _get_view_playlists(self, playlist_ids=[]):
        """
            Get playlists view for playlists
            @param playlist_ids as [int]
            @return View
        """
        view_type = ViewType.DND | ViewType.PLAYLISTS | ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.SMALL
        if len(playlist_ids) == 1 and\
                App().playlists.get_smart(playlist_ids[0]):
            from lollypop.view_playlists import SmartPlaylistsView
            view = self._stack.search_history(SmartPlaylistsView,
                                              {"playlist_ids": playlist_ids,
                                               "view_type": view_type})
            if view is None:
                view = SmartPlaylistsView(playlist_ids, view_type)
        elif playlist_ids:
            from lollypop.view_playlists import PlaylistsView
            view = self._stack.search_history(PlaylistsView,
                                              {"playlist_ids": playlist_ids,
                                               "view_type": view_type})
            if view is None:
                view = PlaylistsView(playlist_ids, view_type)
        else:
            view_type = ViewType.SCROLLED
            if App().window.is_adaptive:
                view_type |= ViewType.MEDIUM
            from lollypop.view_playlists_manager import PlaylistsManagerView
            view = self._stack.search_history(PlaylistsManagerView,
                                              {"obj": None,
                                               "view_type": view_type})
            if view is None:
                view = PlaylistsManagerView(None, view_type)
        view.populate()
        return view

    def _get_view_device_playlists(self, index):
        """
            Show playlists for device at index
            @param index as int
        """
        view_type = ViewType.SCROLLED | ViewType.NO_HISTORY
        from lollypop.view_playlists_manager import PlaylistsManagerDeviceView
        view = PlaylistsManagerDeviceView(index, view_type)
        view.populate()
        return view

    def _get_view_artists_rounded(self):
        """
            Get rounded artists view
            @return view
        """
        from lollypop.view_artists_rounded import RoundedArtistsView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = self._stack.search_history(RoundedArtistsView,
                                          {"view_type": view_type})
        if view is None:
            view = RoundedArtistsView(view_type)
            self._stack.add(view)
            view.populate()
            view.show()
        return view

    def _get_view_artists(self, genre_ids, artist_ids):
        """
            Get artists view for genres/artists
            @param genre_ids as [int]
            @param artist_ids as [int]
        """
        if App().window.is_adaptive:
            view_type = ViewType.MEDIUM | ViewType.SCROLLED
            from lollypop.view_artist_small import ArtistViewSmall
            view = self._stack.search_history(ArtistViewSmall,
                                              {"genre_ids": genre_ids,
                                               "artist_ids": artist_ids,
                                               "view_type": view_type})
            if view is None:
                view = ArtistViewSmall(genre_ids, artist_ids, view_type)
                view.populate()
        else:
            view_type = ViewType.TWO_COLUMNS | ViewType.SCROLLED
            from lollypop.view_artist import ArtistView
            view = self._stack.search_history(ArtistView,
                                              {"genre_ids": genre_ids,
                                               "artist_ids": artist_ids,
                                               "view_type": view_type})
            if view is None:
                view = ArtistView(genre_ids, artist_ids, view_type)
                view.populate()
        view.show()
        return view

    def _get_view_albums_decades(self):
        """
            Get album view for decades
        """
        from lollypop.view_albums_decade_box import AlbumsDecadeBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = self._stack.search_history(AlbumsDecadeBoxView,
                                          {"view_type": view_type})
        if view is None:
            view = AlbumsDecadeBoxView(view_type)
            view.populate()
            view.show()
        return view

    def _get_view_album(self, album):
        """
            Show album
            @param album as Album
        """
        from lollypop.view_album import AlbumView
        view_type = ViewType.TWO_COLUMNS | ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.SMALL
        view = self._stack.search_history(AlbumView,
                                          {"album": album,
                                           "view_type": view_type})
        if view is None:
            view = AlbumView(album, view_type)
            view.populate()
        return view

    def _get_view_genres(self):
        """
            Get view for genres
        """
        from lollypop.view_albums_genre_box import AlbumsGenreBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = self._stack.search_history(AlbumsGenreBoxView,
                                          {"view_type": view_type})
        if view is None:
            view = AlbumsGenreBoxView(view_type)
            view.populate()
            view.show()
        return view

    def _get_view_albums_years(self, years):
        """
            Get album view for years
            @param years as [int]
        """
        from lollypop.view_albums_box import AlbumsYearsBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = self._stack.search_history(AlbumsYearsBoxView,
                                          {"genre_ids": [Type.YEARS],
                                           "artist_ids": years,
                                           "view_type": view_type})
        if view is None:
            view = AlbumsYearsBoxView([Type.YEARS], years, view_type)
            view.populate()
        return view

    def _get_view_albums(self, genre_ids, artist_ids):
        """
            Get albums view for genres/artists
            @param genre_ids as [int]
            @param is compilation as bool
        """
        from lollypop.view_albums_box import AlbumsBoxView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = self._stack.search_history(AlbumsBoxView,
                                          {"genre_ids": genre_ids,
                                           "artist_ids": artist_ids,
                                           "view_type": view_type})
        if view is None:
            view = AlbumsBoxView(genre_ids, artist_ids, view_type)
            view.populate()
        return view

    def _get_view_device_albums(self, index):
        """
            Show albums for device at index
            @param index as int
        """
        from lollypop.view_albums_box_load import AlbumsDeviceBoxView
        view_type = ViewType.SCROLLED | ViewType.NO_HISTORY
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = AlbumsDeviceBoxView(index, view_type)
        view.populate()
        return view

    def _get_view_radios(self):
        """
            Get radios view
            @return RadiosView
        """
        from lollypop.view_radios import RadiosView
        view_type = ViewType.SCROLLED
        if App().window.is_adaptive:
            view_type |= ViewType.MEDIUM
        view = self._stack.search_history(RadiosView,
                                          {"view_type": view_type})
        if view is None:
            view = RadiosView(view_type)
            view.populate()
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
        return view

    def _get_view_settings(self, item_id):
        """
            Show settings views
            @param item_id as int
        """
        if item_id == Type.SETTINGS:
            from lollypop.view_settings import SettingsView
            view = SettingsView(ViewType.SCROLLED)
        else:
            from lollypop.view_settings import SettingsChildView
            view = SettingsChildView(item_id, ViewType.SCROLLED)
        return view

############
# PRIVATE  #
############
