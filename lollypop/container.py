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

from gi.repository import Gtk, GLib

from lollypop.define import App, SidebarContent, Type, ViewType
from lollypop.view import View
from lollypop.adaptive import AdaptiveStack
from lollypop.container_notification import NotificationContainer
from lollypop.container_scanner import ScannerContainer
from lollypop.container_playlists import PlaylistsContainer
from lollypop.container_lists import ListsContainer
from lollypop.container_views import ViewsContainer
from lollypop.progressbar import ProgressBar


class Container(Gtk.Overlay, NotificationContainer,
                ScannerContainer, PlaylistsContainer,
                ListsContainer, ViewsContainer):
    """
        Main view management
    """

    def __init__(self, view_type=ViewType.DEFAULT):
        """
            Init container
            @param view_type as ViewType, will be appended to any created view
        """
        Gtk.Overlay.__init__(self)
        NotificationContainer.__init__(self)
        ScannerContainer.__init__(self)
        PlaylistsContainer.__init__(self)
        ListsContainer.__init__(self)
        ViewsContainer.__init__(self)
        self._view_type = view_type
        self._rounded_artists_view = None
        self._stack = AdaptiveStack()
        self._stack.show()
        self.__setup_view()
        self.add(self._paned_one)

    def stop_all(self):
        """
            Stop current view from processing
        """
        view = self._stack.get_visible_child()
        if view is not None:
            view.stop()

    def reload_view(self):
        """
            Reload current view
        """
        if App().settings.get_value("show-sidebar"):
            ListsContainer._restore_state(self)
        else:
            ViewsContainer._restore_state(self)

    def show_sidebar(self, show):
        """
            Show/Hide navigation sidebar
            @param show as bool
        """
        def select_list_one(selection_list):
            ListsContainer._restore_state(self)
            self._list_one.disconnect_by_func(select_list_one)

        if self._rounded_artists_view is not None:
            self._rounded_artists_view.destroy()
            self._rounded_artists_view = None

        if show:
            self._setup_lists()
            self._list_one.show()
            if len(self._stack.get_children()) == 1:
                App().window.emit("can-go-back-changed", False)
            self._list_one.connect("populated", select_list_one)
            self.update_list_one()
            self.__show_settings_dialog()
        else:
            if self._list_one is not None:
                self._list_one.destroy()
                self._list_two.destroy()
                self._list_one = self._list_two = None
            App().window.emit("show-can-go-back", True)
            empty = len(self._stack.get_children()) == 0
            App().window.emit("can-go-back-changed", not empty)
            # Remove any existing child
            children = self._stack.get_children()
            for child in children:
                self._stack.remove(child)
            # Be sure to have an initial artist view
            if self._rounded_artists_view is None:
                self._rounded_artists_view = self._get_view_artists_rounded(
                    True)
                self._stack.set_visible_child(self._rounded_artists_view)
            if empty:
                ViewsContainer._restore_state(self)
            else:
                # Add children now we have an initial artist view
                for child in children:
                    self._stack.add(child)
                    self._stack.set_visible_child(child)

    def show_artists_albums(self, artist_ids):
        """
            Show albums from artists
            @param artist_ids as [int]
        """
        # FIXME nécessaire?
        def select_list_two(selection_list, artist_ids):
            self._list_two.select_ids(artist_ids)
            self._list_two.disconnect_by_func(select_list_two)
        sidebar_content = App().settings.get_enum("sidebar-content")
        if sidebar_content == SidebarContent.GENRES:
            # Get artist genres
            genre_ids = []
            for artist_id in artist_ids:
                album_ids = App().artists.get_albums(artist_ids)
                for album_id in album_ids:
                    for genre_id in App().albums.get_genre_ids(album_id):
                        if genre_id not in genre_ids:
                            genre_ids.append(genre_id)
            self.show_lists(genre_ids, artist_ids)
        elif sidebar_content == SidebarContent.ARTISTS:
            # Select artists on list one
            self.show_lists(artist_ids, [])
        else:
            self.show_view(artist_ids)

    @property
    def view(self):
        """
            Get current view
            @return View
        """
        view = self._stack.get_visible_child()
        if view is not None and isinstance(view, View):
            return view
        return None

    @property
    def stack(self):
        """
            Container stack
            @return stack as Gtk.Stack
        """
        return self._stack

    @property
    def progress(self):
        """
            Progress bar
            @return ProgressBar
        """
        return self.__progress

    @property
    def rounded_artists_view(self):
        """
            Get rounder artists view
            @return RoundedArtistsView
        """
        return self._rounded_artists_view

############
# PRIVATE  #
############
    def __setup_view(self):
        """
            Setup window main view:
                - genre list
                - artist list
                - main view as artist view or album view
        """
        self._paned_one = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self._paned_two = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)

        self._paned_one.connect("notify::position", self.__on_paned_position)
        self._paned_two.connect("notify::position", self.__on_paned_position)

        self.__progress = ProgressBar()
        self.__progress.get_style_context().add_class("progress-bottom")
        self.__progress.set_property("valign", Gtk.Align.END)
        self.add_overlay(self.__progress)

        self._paned_two.add2(self._stack)
        self._paned_one.add2(self._paned_two)
        position = App().settings.get_value(
            "paned-mainlist-width").get_int32()
        self._paned_one.set_position(position)
        self._paned_one.show()
        self._paned_two.show()
        search_action = App().lookup_action("search")
        search_action.connect("activate", self.__on_search_activate)

    def __show_settings_dialog(self):
        """
            Show settings dialog if view exists in stack
        """
        from lollypop.view_settings import SettingsChildView
        from lollypop.view_settings import SettingsView
        if isinstance(self.view, SettingsChildView) or\
                isinstance(self.view, SettingsView):
            action = App().lookup_action("settings")
            GLib.idle_add(action.activate,
                          GLib.Variant("i", self.view.type))

    def __on_search_activate(self, action, variant):
        """
            @param action as Gio.SimpleAction
            @param variant as GLib.Variant
        """
        if App().window.is_adaptive:
            search = variant.get_string()
            App().window.container.show_view([Type.SEARCH], search)

    def __on_paned_position(self, paned, param):
        """
            Save paned position
            @param paned as Gtk.Paned
            @param param as GParamSpec
        """
        position = paned.get_property(param.name)
        # We do not want to save position while adaptive mode is set
        # Not a good a fix but a working one
        if position < 100:
            return
        if paned == self._paned_one:
            setting = "paned-mainlist-width"
        else:
            setting = "paned-listview-width"
        App().settings.set_value(setting,
                                 GLib.Variant("i",
                                              position))
