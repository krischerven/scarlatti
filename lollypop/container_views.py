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

from gi.repository import Gtk

from lollypop.define import App, Type, ViewType, MARGIN_SMALL


class ViewsContainer:
    """
        Views management for main view
    """

    def __init__(self):
        """
            Init container
        """
        pass

    def show_widget(self, widget):
        """
            Show widget
            @param widget as Gtk.Widget
        """
        from lollypop.view import View
        view = View()
        view.show()
        view.add(widget)
        widget.set_vexpand(True)
        self._stack.add(view)
        self._stack.set_visible_child(view)

    def show_menu(self, widget):
        """
            Show menu widget
            @param widget as Gtk.Widget
        """
        def on_closed(widget, view):
            App().window.toolbar.end.detach_menus()
            self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP)
            self.go_back()
            self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            App().enable_special_shortcuts(True)
            if self.can_go_back:
                self.emit("can-go-back-changed", True)

        from lollypop.view import View
        view = View(ViewType.SCROLLED)
        view.show()
        view.add_widget(widget)
        widget.get_style_context().add_class("adaptive-menu")
        widget.set_vexpand(True)
        widget.connect("closed", on_closed, view)
        self._stack.add(view)
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_DOWN)
        self._stack.set_visible_child(view)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.emit("can-go-back-changed", False)
        App().enable_special_shortcuts(False)

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
            elif item_ids[0] == Type.SUGGESTIONS:
                self.sidebar.select_ids([])
                view = self._get_view_suggestions()
            elif item_ids[0] == Type.SEARCH:
                view = self.get_view_search(data)
            elif item_ids[0] == Type.INFO:
                view = self._get_view_info()
            elif item_ids[0] == Type.DEVICE_ALBUMS:
                view = self._get_view_device_albums(data)
            elif item_ids[0] == Type.DEVICE_PLAYLISTS:
                view = self._get_view_device_playlists(data)
            elif item_ids[0] == Type.LYRICS:
                view = self._get_view_lyrics()
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
                view = self._get_view_playlists(data)
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
                view = self._get_view_albums(item_ids, [])
            elif item_ids[0] == Type.ARTISTS:
                view = self._get_view_artists([], data)
        self._sidebar.select_ids(item_ids, False)
        if view is not None:
            self.set_focused_view(view)
            ids = self._sidebar.selected_ids
            if ids:
                view.set_sidebar_id(ids[0])
            view.show()
            self._stack.add(view)
            if switch:
                self._stack.set_visible_child(view)

    def get_view_current(self):
        """
            Get view for current playlist
            @return View
        """
        from lollypop.view_current_albums import CurrentAlbumsView
        # Search view in children
        for child in self._stack.get_children():
            if isinstance(child, CurrentAlbumsView):
                return child
        view = CurrentAlbumsView(ViewType.DND)
        view.populate()
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
        view.set_search(search)
        view.populate()
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
        if genre_ids and genre_ids[0] == Type.POPULARS:
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
        elif genre_ids and genre_ids[0] == Type.COMPILATIONS:
            items = App().albums.get_compilation_ids([])
        elif genre_ids and not artist_ids:
            if App().settings.get_value("show-compilations-in-album-view"):
                items = App().albums.get_compilation_ids(genre_ids)
            items += App().albums.get_ids([], genre_ids)
        else:
            items = App().albums.get_ids(artist_ids, genre_ids)
        return items

##############
# PROTECTED  #
##############
    def _get_view_playlists(self, playlist_id=None):
        """
            Get playlists view for playlists
            @param playlist_id as int
            @return View
        """
        view_type = ViewType.PLAYLISTS | ViewType.SCROLLED
        if playlist_id is None:
            from lollypop.view_playlists_manager import PlaylistsManagerView
            view = PlaylistsManagerView(view_type)
        elif App().playlists.get_smart(playlist_id):
            from lollypop.view_playlists import SmartPlaylistsView
            view = SmartPlaylistsView(playlist_id, view_type)
        else:
            from lollypop.view_playlists import PlaylistsView
            view_type |= ViewType.DND
            view = PlaylistsView(playlist_id, view_type)
        view.populate()
        return view

    def _get_view_device_playlists(self, index):
        """
            Show playlists for device at index
            @param index as int
        """
        view_type = ViewType.SCROLLED
        from lollypop.view_playlists_manager import PlaylistsManagerDeviceView
        view = PlaylistsManagerDeviceView(index, view_type)
        view.populate()
        return view

    def _get_view_lyrics(self):
        """
            Show lyrics for track
            @pram track as Track
        """
        from lollypop.view_lyrics import LyricsView
        view = LyricsView()
        view.populate(App().player.current_track)
        view.show()
        return view

    def _get_view_artists_rounded(self):
        """
            Get rounded artists view
            @return view
        """
        from lollypop.view_artists_rounded import RoundedArtistsViewWithBanner
        view = RoundedArtistsViewWithBanner()
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
        from lollypop.view_artist import ArtistView
        view = ArtistView(genre_ids, artist_ids)
        view.populate()
        view.show()
        return view

    def _get_view_suggestions(self):
        """
            Get home view
        """
        from lollypop.view_suggestions import SuggestionsView
        view = SuggestionsView()
        view.populate()
        view.show()
        return view

    def _get_view_albums_decades(self):
        """
            Get album view for decades
        """
        from lollypop.view_decades_box import DecadesBoxView
        view = DecadesBoxView()
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
        view = AlbumView(album, view_type)
        view.populate()
        return view

    def _get_view_genres(self):
        """
            Get view for genres
        """
        from lollypop.view_genres_box import GenresBoxView
        view = GenresBoxView()
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
        view = AlbumsYearsBoxView([Type.YEARS], years, view_type)
        view.populate()
        return view

    def _get_view_albums(self, genre_ids, artist_ids):
        """
            Get albums view for genres/artists
            @param genre_ids as [int]
            @param is compilation as bool
        """
        from lollypop.view_albums_box import AlbumsGenresBoxView
        view_type = ViewType.SCROLLED
        view = AlbumsGenresBoxView(genre_ids, artist_ids, view_type)
        view.populate()
        return view

    def _get_view_device_albums(self, index):
        """
            Show albums for device at index
            @param index as int
        """
        from lollypop.view_albums_box import AlbumsDeviceBoxView
        view_type = ViewType.SCROLLED
        view = AlbumsDeviceBoxView(index, view_type)
        view.populate()
        return view

    def _get_view_radios(self):
        """
            Get radios view
            @return RadiosView
        """
        from lollypop.view_radios import RadiosView
        view = RadiosView()
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
