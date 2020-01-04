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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _

from lollypop.define import App, StorageType
from lollypop.define import ViewType, MARGIN
from lollypop.search_local import LocalSearch
from lollypop.view import View
from lollypop.objects_album import Album
from lollypop.objects_track import Track
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.view_artists_line import ArtistsSearchLineView
from lollypop.view_albums_line import AlbumsSearchLineView
from lollypop.view_tracks_search import SearchTracksView
from lollypop.widgets_banner_search import SearchBannerWidget


class SearchView(View, Gtk.Bin, SignalsHelper):
    """
        View for searching albums/tracks
    """

    @signals_map
    def __init__(self, view_type, initial_search=""):
        """
            Init Popover
            @param view_type as ViewType
            @param initial_search as str
        """
        View.__init__(self, view_type | ViewType.SCROLLED | ViewType.OVERLAY)
        Gtk.Bin.__init__(self)
        self.__timeout_id = None
        self.__current_search = ""
        self.__local_search = LocalSearch()
        self.__searches_count = 0
        self.__cancellable = Gio.Cancellable()
        self._empty_message = _("Search for artists, albums and tracks")
        self._empty_icon_name = "edit-find-symbolic"
        self.__cancellable = Gio.Cancellable()
        self.__banner = SearchBannerWidget()
        self.__banner.show()
        self.__grid = Gtk.Grid()
        self.__grid.show()
        self.__grid.set_row_spacing(MARGIN)
        self.__grid.get_style_context().add_class("opacity-transition-fast")
        self.__grid.get_style_context().add_class("padding")
        self.__grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__grid.set_property("valign", Gtk.Align.START)
        self.__artists_line_view = ArtistsSearchLineView()
        self.__albums_line_view = AlbumsSearchLineView()
        self.__search_tracks_view = SearchTracksView()
        self.__grid.add(self.__search_tracks_view)
        self.__grid.add(self.__artists_line_view)
        self.__grid.add(self.__albums_line_view)
        self.add_widget(self.__grid, self.__banner)
        self.__banner.entry.connect("changed", self._on_search_changed)
        self.set_search(initial_search)
        self.show_placeholder(True,
                              _("Search for artists, albums and tracks"))
        return [
                (self.__local_search, "match-artist",
                 "_on_local_match_artist"),
                (self.__local_search, "match-album",
                 "_on_local_match_album"),
                (self.__local_search, "match-track",
                 "_on_local_match_track"),
                (self.__local_search, "search-finished",
                 "_on_search_finished"),
                (App().spotify, "match-artist",
                 "_on_local_match_artist"),
                (App().spotify, "match-album",
                 "_on_local_match_album"),
                (App().spotify, "match-track",
                 "_on_local_match_track"),
                (App().spotify, "search-finished",
                 "_on_search_finished"),
        ]

    def populate(self):
        """
            Populate search
            in db based on text entry current text
        """
        # FIXME
        self.__search_empty = True
        self.__albums_line_view.clear()
        self.__artists_line_view.clear()
        self.__search_tracks_view.clear()
        self.cancel()
        if len(self.__current_search) > 1:
            self.__banner.spinner.start()
            current_search = self.__current_search.lower()
            self.__local_search.get(
                       current_search,
                       StorageType.COLLECTION | StorageType.SAVED,
                       self.__cancellable)
            self.__searches_count += 1
            if App().settings.get_value("search-spotify"):
                self.__searches_count += 2
                self.__local_search.get(
                           current_search,
                           StorageType.EPHEMERAL |
                           StorageType.SPOTIFY_NEW_RELEASES,
                           self.__cancellable)
                App().task_helper.run(App().spotify.search,
                                      current_search,
                                      self.__cancellable)
        else:
            self.show_placeholder(True,
                                  _("Search for artists, albums and tracks"))
            self.__banner.spinner.stop()

    def set_search(self, search):
        """
            Set search text
            @param search as str
        """
        self.__current_search = search.strip()
        self.__banner.entry.set_text(search)
        self.__banner.entry.grab_focus()

    def grab_focus(self):
        """
            Make search entry grab focus
        """
        self.__banner.entry.grab_focus()

    def cancel(self):
        """
            Cancel current search and replace cancellable
        """
        self.__cancellable.cancel()
        self.__cancellable = Gio.Cancellable()

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        search = self.__banner.entry.get_text().strip()
        return {"view_type": self.view_type, "initial_search": search}

#######################
# PROTECTED           #
#######################
    def _on_map(self, widget):
        """
            Disable shortcuts and update buttons
            @param widget as Gtk.Widget
        """
        View._on_map(self, widget)
        App().enable_special_shortcuts(False)

    def __on_unmap(self, widget):
        """
            Cancel current loading and enable shortcuts
            @param widget as Gtk.Widget
        """
        View._on_unmap(self, widget)
        App().enable_special_shortcuts(True)
        self.cancel()
        self.__view.stop()
        self.__banner.spinner.stop()

    def _on_local_match_artist(self, local_search, artist_id):
        """
            Add a new artist to view
            @param local_search as LocalSearch
            @param artist_id as int
        """
        self.__artists_line_view.show()
        self.__artists_line_view.add_value(artist_id)
        self.show_placeholder(False)

    def _on_local_match_album(self, local_search, album_id):
        """
            Add a new album to view
            @param local_search as LocalSearch
            @param artist_id as int
        """
        self.__albums_line_view.show()
        self.__albums_line_view.add_album(Album(album_id))
        self.show_placeholder(False)

    def _on_local_match_track(self, local_search, track_id):
        """
            Add a new track to view
            @param local_search as LocalSearch
            @param track_id as int
        """
        self.__search_tracks_view.show()
        self.__search_tracks_view.append_row(Track(track_id))
        self.show_placeholder(False)

    def _on_search_finished(self, *ignore):
        """
            Stop spinner and show placeholder if not result
        """
        self.__banner.spinner.stop()
        self.__searches_count -= 1
        empty = len(self.__albums_line_view.children) == 0 and\
            len(self.__search_tracks_view.get_children()) == 0 and\
            len(self.__artists_line_view.children) == 0
        if self.__searches_count == 0 and empty:
            self.show_placeholder(True, _("No results for this search"))
        else:
            self.__grid.set_state_flags(Gtk.StateFlags.VISITED, True)
            GLib.idle_add(self.__albums_line_view.update_buttons)
            GLib.idle_add(self.__artists_line_view.update_buttons)

#######################
# PRIVATE             #
#######################
    def __set_no_result_placeholder(self):
        """
            Set placeholder for no result
        """
        self.__placeholder.set_text()

    def __on_search_get(self, result, search, storage_type):
        """
            Add rows for internal results
            @param result as [(int, Album, bool)]
        """
        if result:
            albums = []
            reveal_albums = []
            for (album, in_tracks) in result:
                albums.append(album)
                if in_tracks:
                    reveal_albums.append(album)
            self.__view.add_reveal_albums(reveal_albums)
            self.__view.populate(albums)
            self.show_placeholder(False)

        if storage_type & StorageType.EPHEMERAL:
            App().task_helper.run(App().spotify.search,
                                  search,
                                  self.__cancellable)
        else:
            self._on_search_finished()

    def _on_search_changed(self, widget):
        """
            Timeout filtering
            @param widget as Gtk.TextEntry
        """
        self.__grid.unset_state_flags(Gtk.StateFlags.VISITED)
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
        self.__timeout_id = GLib.timeout_add(
                500,
                self.__on_search_changed_timeout)

    def __on_search_changed_timeout(self):
        """
            Populate widget
        """
        self.__timeout_id = None
        new_search = self.__banner.entry.get_text().strip()
        if self.__current_search != new_search:
            self.__current_search = new_search
            self.populate()

    def __on_button_clicked(self, button):
        """
            Reload search for current button
            @param button as Gtk.RadioButton
        """
        if button.get_active():
            self.__current_search = self.__banner.entry.get_text().strip()
            if self.__current_search:
                self.populate()
