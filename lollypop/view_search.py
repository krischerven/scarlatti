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
from lollypop.define import Size, ViewType
from lollypop.view_albums_list import AlbumsListView
from lollypop.search import Search
from lollypop.utils import get_network_available, get_youtube_dl
from lollypop.view import View
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.widgets_banner_search import SearchBannerWidget


class SearchView(View, Gtk.Bin, SignalsHelper):
    """
        View for searching albums/tracks
    """

    @signals_map
    def __init__(self, view_type):
        """
            Init Popover
            @param view_type as ViewType
        """
        View.__init__(self, view_type | ViewType.SCROLLED | ViewType.OVERLAY)
        Gtk.Bin.__init__(self)
        self.__timeout_id = None
        self.__current_search = ""
        self.__cancellable = Gio.Cancellable()
        self._empty_message = _("Search for artists, albums and tracks")
        self._empty_icon_name = "edit-find-symbolic"
        self.__cancellable = Gio.Cancellable()
        self.__search_type_action = Gio.SimpleAction.new_stateful(
                                               "search_type",
                                               GLib.VariantType.new("s"),
                                               GLib.Variant("s", ""))
        self.__search_type_action.connect("change-state",
                                          self.__on_search_action_change_state)
        App().add_action(self.__search_type_action)
        self.__bottom_buttons = Gtk.Grid()
        self.__bottom_buttons.show()
        self.__bottom_buttons.get_style_context().add_class("linked")
        self.__bottom_buttons.set_property("halign", Gtk.Align.CENTER)
        local_button = Gtk.RadioButton.new()
        local_button.show()
        local_button.set_property("draw-indicator", False)
        image = Gtk.Image.new_from_icon_name("computer-symbolic",
                                             Gtk.IconSize.BUTTON)
        image.show()
        local_button.set_image(image)
        local_button.set_action_name("app.search_type")
        local_button.set_action_target_value(GLib.Variant("s", "local"))
        local_button.set_size_request(125, -1)
        web_button = Gtk.RadioButton.new_from_widget(local_button)
        web_button.show()
        web_button.set_property("draw-indicator", False)
        image = Gtk.Image.new_from_icon_name("goa-panel-symbolic",
                                             Gtk.IconSize.BUTTON)
        image.show()
        web_button.set_image(image)
        web_button.set_action_name("app.search_type")
        web_button.set_action_target_value(GLib.Variant("s", "web"))
        web_button.set_size_request(125, -1)
        self.__bottom_buttons.add(local_button)
        self.__bottom_buttons.add(web_button)
        self.__view = AlbumsListView([], [], view_type & ~ViewType.SCROLLED)
        self.__view.show()
        self.__view.set_external_scrolled(self._scrolled)
        self.__view.set_width(Size.MEDIUM)
        self.__view.get_style_context().add_class("padding")
        self.__banner = SearchBannerWidget(self.__view)
        self.__banner.show()
        self.__banner.connect("scroll", self._on_banner_scroll)
        self.add_widget(self.__view, self.__banner)
        self.add(self.__bottom_buttons)
        self.__banner.entry.connect("changed", self._on_search_changed)
        return [
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
        self.__view.stop()
        self.__view.clear()
        self.cancel()
        if len(self.__current_search) > 1:
            self.__banner.spinner.start()
            state = self.__search_type_action.get_state().get_string()
            current_search = self.__current_search.lower()
            search = Search()
            if state == "local":
                search.get(current_search,
                           StorageType.COLLECTION | StorageType.SAVED,
                           self.__cancellable,
                           callback=(self.__on_search_get,
                                     current_search,
                                     StorageType.COLLECTION |
                                     StorageType.SAVED))
            elif state == "web":
                search.get(current_search,
                           StorageType.EPHEMERAL |
                           StorageType.SPOTIFY_NEW_RELEASES,
                           self.__cancellable,
                           callback=(self.__on_search_get,
                                     current_search,
                                     StorageType.EPHEMERAL |
                                     StorageType.SPOTIFY_NEW_RELEASES,))
        else:
            self.show_placeholder(True,
                                  _("Search for artists, albums and tracks"))
            GLib.idle_add(self.__banner.spinner.stop)

    def set_search(self, search):
        """
            Set search text
            @param search as str
        """
        parsed = urlparse(search)
        search = search.replace("%s://" % parsed.scheme, "")
        if parsed.scheme == "local":
            self.__banner.entry.set_text(search)
            GLib.idle_add(self.__search_type_action.set_state,
                          GLib.Variant("s", "local"))
        elif parsed.scheme == "web":
            self.__banner.entry.set_text(search)
            GLib.idle_add(self.__search_type_action.set_state,
                          GLib.Variant("s", "web"))
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
        if self.__search_type_action.get_state().get_string() == "local":
            search = "local://%s" % self.__banner.entry.get_text()
        else:
            search = "web://%s" % self.__banner.entry.get_text()
        return {"view_type": self.view_type, "search": search}

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
        self.__search_type_action.change_state(GLib.Variant("s", "local"))

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

    def _on_new_spotify_album(self, spotify, album):
        """
            Add album
            @param spotify as SpotifyHelper
            @param album as Album
        """
        self.show_placeholder(False)
        self.__view.insert_album(album, len(album.tracks) == 1, -1)

    def _on_search_finished(self, *ignore):
        """
            Stop spinner and show placeholder if not result
        """
        self.__banner.spinner.stop()
        if not self.__view.children:
            self.show_placeholder(True, _("No results for this search"))

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
            self.__view.set_reveal(reveal_albums)
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
        state = self.__search_type_action.get_state().get_string()
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

    def __on_search_action_change_state(self, action, value):
        """
            Update action value
            @param action as Gio.SimpleAction
            @param value as GLib.Variant
        """
        if value != action.get_state():
            action.set_state(value)
            self.__current_search = self.__banner.entry.get_text().strip()
            self.populate()
