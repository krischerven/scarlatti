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
from urllib.parse import urlparse

from lollypop.define import App, StorageType
from lollypop.define import ViewType, MARGIN_SMALL
from lollypop.search_local import LocalSearch
from lollypop.utils import get_network_available, get_youtube_dl
from lollypop.view import View
from lollypop.objects_album import Album
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.view_artists_line import ArtistsSearchLineView
from lollypop.view_albums_line import AlbumsSearchLineView
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
        self.__search_empty = True
        self.__cancellable = Gio.Cancellable()
        self._empty_message = _("Search for artists, albums and tracks")
        self._empty_icon_name = "edit-find-symbolic"
        self.__cancellable = Gio.Cancellable()
        self.__bottom_buttons = Gtk.Grid()
        self.__bottom_buttons.show()
        self.__bottom_buttons.set_property("halign", Gtk.Align.CENTER)
        self.__bottom_buttons.set_margin_bottom(MARGIN_SMALL)
        self.__bottom_buttons.get_style_context().add_class("linked")
        self.__local_button = Gtk.RadioButton.new()
        self.__local_button.show()
        self.__local_button.set_property("draw-indicator", False)
        self.__local_button.set_name("local")
        self.__local_button.get_style_context().add_class("light-button")
        image = Gtk.Image.new_from_icon_name("computer-symbolic",
                                             Gtk.IconSize.BUTTON)
        image.show()
        self.__local_button.set_image(image)
        self.__local_button.set_size_request(125, -1)
        web_button = Gtk.RadioButton.new_from_widget(self.__local_button)
        web_button.show()
        web_button.set_property("draw-indicator", False)
        web_button.set_name("web")
        web_button.get_style_context().add_class("light-button")
        image = Gtk.Image.new_from_icon_name("goa-panel-symbolic",
                                             Gtk.IconSize.BUTTON)
        image.show()
        web_button.set_image(image)
        web_button.set_size_request(125, -1)
        self.__bottom_buttons.add(self.__local_button)
        self.__bottom_buttons.add(web_button)
        self.__banner = SearchBannerWidget(None)
        self.__banner.show()
        grid = Gtk.Grid()
        grid.show()
        grid.get_style_context().add_class("padding")
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.__artists_line_view = ArtistsSearchLineView()
        self.__artists_line_view.show()
        self.__albums_line_view = AlbumsSearchLineView()
        self.__albums_line_view.show()
        grid.add(self.__artists_line_view)
        grid.add(self.__albums_line_view)
        self.add_widget(grid, self.__banner)
        self.add(self.__bottom_buttons)
        self.__banner.entry.connect("changed", self._on_search_changed)
        self.set_search(initial_search)
        self.__local_button.connect("clicked", self.__on_button_clicked)
        web_button.connect("clicked", self.__on_button_clicked)
        self.show_placeholder(True,
                              _("Search for artists, albums and tracks"))
        return [
                (self.__local_search, "match-artist",
                 "_on_local_match_artist"),
                (self.__local_search, "match-album",
                 "_on_local_match_album"),
                (self.__local_search, "search-finished",
                 "_on_search_finished"),
                (App().spotify, "new-album", "_on_new_spotify_album"),
                (App().spotify, "search-finished", "_on_search_finished"),
                (App().settings, "changed::network-access",
                 "_update_bottom_buttons"),
                (App().settings, "changed::network-access-acl",
                 "_update_bottom_buttons")
        ]

    def populate(self):
        """
            Populate search
            in db based on text entry current text
        """
        # FIXME
        self.__search_empty = True
        self.__artists_line_view.clear()
        self.cancel()
        if len(self.__current_search) > 1:
            self.__banner.spinner.start()
            state = self.__get_current_search_state()
            current_search = self.__current_search.lower()
            if state == "local":
                self.__local_search.get(
                           current_search,
                           StorageType.COLLECTION | StorageType.SAVED,
                           self.__cancellable)
            elif state == "web":
                pass
        else:
            self.show_placeholder(True,
                                  _("Search for artists, albums and tracks"))
            self.__banner.spinner.stop()

    def set_search(self, search):
        """
            Set search text
            @param search as str
        """
        parsed = urlparse(search)
        search = search.replace("%s://" % parsed.scheme, "")
        self.__current_search = search.strip()
        self.__set_current_search_state(parsed.scheme)
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
        if self.__get_current_search_state() == "local":
            search = "local://%s" % self.__banner.entry.get_text()
        else:
            search = "web://%s" % self.__banner.entry.get_text()
        return {"view_type": self.view_type, "initial_search": search}

#######################
# PROTECTED           #
#######################
    def _update_bottom_buttons(self, *ignore):
        """
            Update bottom buttons based on current state
        """
        (path, env) = get_youtube_dl()
        if path is None or\
                not get_network_available("SPOTIFY") or\
                not get_network_available("YOUTUBE"):
            self.__bottom_buttons.hide()
        else:
            self.__bottom_buttons.show()

    def _on_map(self, widget):
        """
            Disable shortcuts and update buttons
            @param widget as Gtk.Widget
        """
        View._on_map(self, widget)
        App().enable_special_shortcuts(False)
        self._update_bottom_buttons()

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
        self.__artists_line_view.add_value(artist_id)
        self.__search_empty = False
        self.show_placeholder(False)

    def _on_local_match_album(self, local_search, album_id):
        """
            Add a new album to view
            @param local_search as LocalSearch
            @param artist_id as int
        """
        self.__albums_line_view.add_album(Album(album_id))
        self.__search_empty = False
        self.show_placeholder(False)

    def _on_new_spotify_album(self, spotify, album):
        """
            Add album
            @param spotify as SpotifySearch
            @param album as Album
        """
        self.__search_empty = False
        self.show_placeholder(False)
        if len(album.tracks) == 1:
            self.__view.add_reveal_albums([album])
        self.__view.insert_album(album, -1)

    def _on_search_finished(self, *ignore):
        """
            Stop spinner and show placeholder if not result
        """
        self.__banner.spinner.stop()
        if self.__search_empty:
            self.show_placeholder(True, _("No results for this search"))

#######################
# PRIVATE             #
#######################
    def __set_current_search_state(self, state):
        """
            Set current search state
            @param state as str
        """
        for button in self.__local_button.get_group():
            if button.get_name() == state:
                button.set_active(True)
                break

    def __get_current_search_state(self):
        """
            Get current search state in buttons group
            @return str
        """
        for button in self.__local_button.get_group():
            if button.get_active():
                return button.get_name()
        return "local"

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
            self.__search_empty = False
            albums = []
            reveal_albums = []
            for (album, in_tracks) in result:
                albums.append(album)
                if in_tracks:
                    reveal_albums.append(album)
            self.__view.add_reveal_albums(reveal_albums)
            self.__view.populate(albums)
            self.show_placeholder(False)
            self.__banner.play_button.set_sensitive(True)
            self.__banner.new_button.set_sensitive(True)

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
        self.__banner.play_button.set_sensitive(False)
        self.__banner.new_button.set_sensitive(False)
        state = self.__get_current_search_state()
        if state == "local":
            timeout = 500
        else:
            timeout = 1000
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
        self.__timeout_id = GLib.timeout_add(
                timeout,
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
