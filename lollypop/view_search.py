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
from random import shuffle
from urllib.parse import urlparse

from lollypop.define import App, Type, Shuffle, MARGIN_SMALL
from lollypop.view_albums_list import AlbumsListView
from lollypop.search import Search
from lollypop.utils import get_network_available
from lollypop.view import View
from lollypop.logger import Logger
from lollypop.helper_size_allocation import SizeAllocationHelper
from lollypop.helper_signals import SignalsHelper


class SearchView(View, Gtk.Bin, SizeAllocationHelper, SignalsHelper):
    """
        View for searching albums/tracks
    """

    def __init__(self, view_type):
        """
            Init Popover
            @param view_type as ViewType
        """
        self.signals = [
            (App().spotify, "new-album", "_on_new_spotify_album"),
            (App().spotify, "search-finished", "_on_search_finished"),
            (App().settings, "changed::network-access",
             "_update_bottom_buttons"),
            (App().settings, "changed::network-access-acl",
             "_update_bottom_buttons")
        ]
        View.__init__(self)
        Gtk.Bin.__init__(self)
        SizeAllocationHelper.__init__(self)
        SignalsHelper.__init__(self)
        self.__timeout_id = None
        self.__signal_ids = {}
        self.__current_search = ""
        self.__cancellable = Gio.Cancellable()
        self.__history = []

        self.__search_type_action = Gio.SimpleAction.new_stateful(
                                               "search_type",
                                               GLib.VariantType.new("s"),
                                               GLib.Variant("s", "local"))
        self.__search_type_action.connect("change-state",
                                          self.__on_search_action_change_state)
        App().add_action(self.__search_type_action)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SearchView.ui")
        self.__widget = builder.get_object("widget")
        self.__new_button = builder.get_object("new_button")
        self.__play_button = builder.get_object("play_button")
        self.__bottom_buttons = builder.get_object("bottom_buttons")
        self.__entry = builder.get_object("entry")
        self.__spinner = builder.get_object("spinner")
        self.__header_stack = builder.get_object("header_stack")
        self.__combo_locale = builder.get_object("combo_locale")
        self.__combo_locale.set_active_id(
            App().settings.get_value("spotify-charts-locale").get_string())
        self.__button_stack = builder.get_object("button_stack")
        self.__stack = builder.get_object("stack")
        self.__placeholder = builder.get_object("placeholder")
        self.__view = AlbumsListView([], [], view_type)
        self.__view.set_margin_start(MARGIN_SMALL)
        self.__view.show()
        self.__stack.add_named(self.__view, "view")
        self.__set_default_placeholder()
        self.add(self.__widget)
        builder.connect_signals(self)
        self.__widget.set_property("halign", Gtk.Align.CENTER)
        self._on_adaptive_changed(App().window, App().window.is_adaptive)

    def populate(self):
        pass

    def set_search(self, search):
        """
            Set search text
            @param search as str
        """
        parsed = urlparse(search)
        search = search.replace("%s://" % parsed.scheme, "")
        if parsed.scheme == "local":
            self.__entry.set_text(search)
            GLib.idle_add(self.__search_type_action.set_state,
                          GLib.Variant("s", "local"))
        elif parsed.scheme == "web":
            self.__entry.set_text(search)
            GLib.idle_add(self.__search_type_action.set_state,
                          GLib.Variant("s", "web"))

    def cancel(self):
        """
            Cancel current search and replace cancellable
        """
        self.__cancellable.cancel()
        self.__cancellable = Gio.Cancellable()

    @property
    def should_destroy(self):
        return False

#######################
# PROTECTED           #
#######################
    def _update_bottom_buttons(self, *ignore):
        """
            Update bottom buttons based on current state
        """
        if GLib.find_program_in_path("youtube-dl") is None or\
                not get_network_available("SPOTIFY") or\
                not get_network_available("YOUTUBE"):
            self.__bottom_buttons.hide()
            self.__search_type_action.change_state(GLib.Variant("s", "local"))
        else:
            self.__bottom_buttons.show()

    def _handle_size_allocate(self, allocation):
        """
            Change view width
            @param allocation as Gtk.Allocation
        """
        if SizeAllocationHelper._handle_size_allocate(self, allocation):
            self.__widget.set_size_request(allocation.width / 2, -1)

    def _on_play_button_clicked(self, button):
        """
            Play search
            @param button as Gtk.Button
        """
        try:
            App().player.clear_albums()
            shuffle_setting = App().settings.get_enum("shuffle")
            children = self.__view.children
            if shuffle_setting == Shuffle.ALBUMS:
                shuffle(children)
            for child in children:
                App().player.add_album(child.album)
            App().player.load(App().player.albums[0].tracks[0])
        except Exception as e:
            Logger.error("SearchPopover::_on_play_button_clicked(): %s", e)

    def _on_new_button_clicked(self, button):
        """
            Create a new playlist based on search
            @param button as Gtk.Button
        """
        App().task_helper.run(self.__search_to_playlist)

    def _on_search_changed(self, widget):
        """
            Timeout filtering
            @param widget as Gtk.TextEntry
        """
        state = self.__search_type_action.get_state().get_string()
        if state == "local":
            timeout = 500
        else:
            timeout = 1000
        if self.__timeout_id:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
        self.cancel()
        self.__view.stop()
        self.__current_search = widget.get_text().strip()
        self.__timeout_id = GLib.timeout_add(
                timeout,
                self.__on_search_changed_timeout)

    def _on_combo_locale_changed(self, combobox):
        """
            Save setting
            @param combobox as Gtk.ComboBoxText
        """
        App().settings.set_value("spotify-charts-locale",
                                 GLib.Variant("s",
                                              combobox.get_active_id()))
        self.__on_search_action_change_state(self.__search_type_action,
                                             GLib.Variant("s", "charts"))

    def _on_map(self, widget):
        """
            Init signals and grab focus
            @param widget as Gtk.Widget
        """
        View._on_map(self, widget)
        App().enable_special_shortcuts(False)
        self._update_bottom_buttons()
        GLib.idle_add(self.__entry.grab_focus)

    def __on_unmap(self, widget):
        """
            Clean up
            @param widget as Gtk.Widget
        """
        View._on_unmap(self, widget)
        App().enable_special_shortcuts(True)
        self.cancel()
        self.__view.stop()
        self.__button_stack.set_visible_child(self.__new_button)
        self.__spinner.stop()

    def _on_new_spotify_album(self, spotify, album, cover_uri):
        """
            Add album
            @param spotify as SpotifyHelper
            @param album as Album
            @param cover_uri as str
        """
        self.__view.insert_album(album, len(album.tracks) == 1, -1, cover_uri)
        self.__stack.set_visible_child_name("view")

    def _on_search_finished(self, api):
        """
            Stop spinner
            @param api ignored
        """
        self.__spinner.stop()
        self.__button_stack.set_visible_child(self.__new_button)
        if not self.__view.children:
            self.__stack.set_visible_child_name("placeholder")
            self.__set_no_result_placeholder()

    def _on_adaptive_changed(self, window, status):
        """
            Handle adaptive mode for views
        """
        style_context = self.__placeholder.get_style_context()
        if status:
            style_context.remove_class("text-xx-large")
            style_context.add_class("text-x-large")
        else:
            style_context.remove_class("text-x-large")
            style_context.add_class("text-xx-large")

#######################
# PRIVATE             #
#######################
    def __set_no_result_placeholder(self):
        """
            Set placeholder for no result
        """
        self.__placeholder.set_text(_("No results for this search"))

    def __set_default_placeholder(self):
        """
            Set placeholder for no result
        """
        self.__placeholder.set_text(_("Search for artists, albums and tracks"))

    def __populate(self):
        """
            Populate searching items
            in db based on text entry current text
        """
        self.__cancellable = Gio.Cancellable()
        self.__button_stack.set_visible_child(self.__spinner)
        self.__history = []
        if len(self.__current_search) > 2:
            self.__spinner.start()
            state = self.__search_type_action.get_state().get_string()
            current_search = self.__current_search.lower()
            if state == "local":
                search = Search()
                search.get(current_search,
                           self.__cancellable,
                           callback=(self.__on_search_get, current_search))
            elif state == "web":
                App().task_helper.run(App().spotify.search,
                                      current_search,
                                      self.__cancellable)
        else:
            self.__stack.set_visible_child_name("placeholder")
            self.__set_default_placeholder()
            self.__button_stack.set_visible_child(self.__new_button)
            GLib.idle_add(self.__spinner.stop)

    def __search_to_playlist(self):
        """
            Create a new playlist based on search
        """
        tracks = []
        for child in self.__view.children:
            tracks += child.album.tracks
        if tracks:
            playlist_id = App().playlists.get_id(self.__current_search)
            if playlist_id == Type.NONE:
                App().playlists.add(self.__current_search)
                playlist_id = App().playlists.get_id(self.__current_search)
            App().playlists.add_tracks(playlist_id, tracks)
        GLib.idle_add(self.__show_playlist, playlist_id)

    def __show_playlist(self, playlist_id):
        """
            Hide if in a popover and show playlist
        """
        App().window.container.show_view(Type.PLAYLISTS, [playlist_id])
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.hide()
        else:
            self.destroy()

    def __on_search_get(self, result, search):
        """
            Add rows for internal results
            @param result as [(int, Album, bool)]
        """
        self._on_search_finished(None)
        if result:
            albums = []
            reveal_albums = []
            for (album, in_tracks) in result:
                albums.append(album)
                if in_tracks:
                    reveal_albums.append(album)
            self.__view.set_reveal(reveal_albums)
            self.__view.populate(albums)
            self.__stack.set_visible_child_name("view")

    def __on_search_changed_timeout(self):
        """
            Populate widget
        """
        if self.__view.children:
            self.__view.stop()
            self.__view.clear()
            return True
        self.__timeout_id = None
        self.__populate()
        if self.__current_search != "":
            self.__new_button.set_sensitive(True)
        else:
            self.__new_button.set_sensitive(False)

    def __on_search_action_change_state(self, action, value):
        """
            Update action value
            @param action as Gio.SimpleAction
            @param value as GLib.Variant
        """
        self.cancel()
        self.__view.stop()
        action.set_state(value)
        state = value.get_string()
        # A new album signal may be in queue, so clear after
        GLib.idle_add(self.__view.clear)
        if state == "local":
            self.__new_button.show()
            self.__button_stack.set_visible_child(self.__new_button)
        else:
            self.__new_button.hide()
        if state == "charts":
            self.__header_stack.set_visible_child_name("locale")
            self.__play_button.set_sensitive(True)
            self.__button_stack.set_visible_child(self.__spinner)
            self.__history = []
            self.__spinner.start()
            self.__stack.set_visible_child_name("view")
            App().task_helper.run(App().spotify.charts,
                                  self.__cancellable,
                                  self.__combo_locale.get_active_id())
        else:
            self.__header_stack.set_visible_child_name("entry")
            self.__populate()
            GLib.idle_add(self.__entry.grab_focus)
