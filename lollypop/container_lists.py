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

from gi.repository import GLib

from gettext import gettext as _

from lollypop.loader import Loader
from lollypop.logger import Logger
from lollypop.objects import Album
from lollypop.selectionlist import SelectionList
from lollypop.define import App, Type, SelectionListMask, SidebarContent


class ListsContainer:
    """
        Selections lists management for main view
    """

    def __init__(self):
        """
            Init container
        """
        self._list_one = self._list_two = None

    def update_list_one(self, update=False):
        """
            Update list one
            @param update as bool
        """
        if self._list_one.get_visible():
            sidebar_content = App().settings.get_enum("sidebar-content")
            if sidebar_content == SidebarContent.GENRES:
                self.__update_list_genres(self._list_one, update)
            elif sidebar_content == SidebarContent.ARTISTS:
                self.__update_list_artists(self._list_one, [Type.ALL], update)
            else:
                self.__update_list_artists(self._list_one, None, update)

    def update_list_two(self, update=False):
        """
            Update list two
            @param update as bool
        """
        if self._list_one.get_visible():
            sidebar_content = App().settings.get_enum("sidebar-content")
            ids = self._list_one.selected_ids
            if ids and ids[0] in [Type.PLAYLISTS, Type.YEARS]:
                self.__update_list_playlists(update, ids[0])
            elif sidebar_content == SidebarContent.GENRES and ids:
                self.__update_list_artists(self._list_two, ids, update)

    def show_lists(self, list_one_ids, list_two_ids):
        """
            Show list one and two
            @param list_one_ids as [int]
            @param list_two_ids as [int]
        """
        def select_list_two(selection_list, list_two_ids):
            self._list_two.select_ids(list_two_ids)
            self._list_two.disconnect_by_func(select_list_two)

        if list_two_ids:
            # Select genres on list one
            self._list_two.connect("populated", select_list_two, list_two_ids)
            self._list_one.select_ids(list_one_ids)
        else:
            self._list_one.select_ids(list_one_ids)

    @property
    def list_one(self):
        """
            Get first SelectionList
            @return SelectionList
        """
        return self._list_one

    @property
    def list_two(self):
        """
            Get second SelectionList
            @return SelectionList
        """
        return self._list_two

##############
# PROTECTED  #
##############
    def _setup_lists(self):
        """
            Add and setup list one and list two
        """
        self._list_one = SelectionList(SelectionListMask.LIST_ONE)
        self._list_two = SelectionList(SelectionListMask.LIST_TWO)
        self._list_one.listbox.connect("row-activated",
                                       self.__on_list_one_activated)
        self._list_two.listbox.connect("row-activated",
                                       self.__on_list_two_activated)
        self._list_one.connect("populated", self.__on_list_one_populated)
        self._list_one.connect("pass-focus", self.__on_pass_focus)
        self._list_two.connect("pass-focus", self.__on_pass_focus)
        self._list_two.connect("map", self.__on_list_two_mapped)
        self._paned_two.add1(self._list_two)
        self._paned_one.add1(self._list_one)
        App().window.add_paned(self._paned_one, self._list_one)
        App().window.add_paned(self._paned_two, self._list_two)
        if App().window.is_adaptive:
            self._list_one.show()
            App().window.update_layout(True)

    def _restore_state(self):
        """
            Restore list state
        """
        def select_list_two(selection_list, ids):
            # For some reasons, we need to delay this
            # If list two is short, we may receive list two selected-item
            # signal before list one
            GLib.idle_add(self._list_two.select_ids, ids)
            self._list_two.disconnect_by_func(select_list_two)
        try:
            state_one_ids = App().settings.get_value("state-one-ids")
            state_two_ids = App().settings.get_value("state-two-ids")
            state_three_ids = App().settings.get_value("state-three-ids")
            # Empty because we do not have any genre set
            if not state_one_ids:
                state_one_ids = state_two_ids
                state_two_ids = state_three_ids
            if state_one_ids:
                self._list_one.select_ids(state_one_ids)
                # If list two not available, directly show view
                sidebar_content = App().settings.get_enum("sidebar-content")
                if state_two_ids and (
                                  App().window.is_adaptive or
                                  sidebar_content == SidebarContent.DEFAULT):
                    self.show_view(state_one_ids, state_two_ids)
                # Wait for list to be populated and select item
                elif state_two_ids and not state_three_ids:
                    self._list_two.connect("populated",
                                           select_list_two,
                                           state_two_ids)

                if state_three_ids:
                    album = Album(state_three_ids[0],
                                  state_one_ids,
                                  state_two_ids)
                    self.show_view([Type.ALBUM], album)
            elif not App().window.is_adaptive:
                self._list_one.select_first()
        except Exception as e:
            Logger.error("ListsContainer::_restore_state(): %s", e)

############
# PRIVATE  #
############
    def __update_list_playlists(self, update, type):
        """
            Setup list for playlists
            @param update as bool
            @param type as int
        """
        self._list_two.mark_as(SelectionListMask.PLAYLISTS)
        if type == Type.PLAYLISTS:
            items = self._list_two.get_playlist_headers()
            items += App().playlists.get()
        else:
            (years, unknown) = App().albums.get_years()
            items = [(year, str(year), str(year)) for year in sorted(years)]
            if unknown:
                items.insert(0, (Type.NONE, _("Unknown"), ""))
        if update:
            self._list_two.update_values(items)
        else:
            self._list_two.populate(items)

    def __update_list_genres(self, selection_list, update):
        """
            Setup list for genres
            @param list as SelectionList
            @param update as bool, if True, just update entries
        """
        def load():
            genres = App().genres.get()
            return genres

        def setup(genres):
            selection_list.mark_as(SelectionListMask.GENRES)
            items = selection_list.get_headers(selection_list.mask)
            items += genres
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)

        loader = Loader(target=load, view=selection_list, on_finished=setup)
        loader.start()

    def __update_list_artists(self, selection_list, genre_ids, update):
        """
            Setup list for artists
            @param list as SelectionList
            @param genre_ids as [int]
            @param update as bool, if True, just update entries
        """
        def load():
            if genre_ids is None:
                compilations = App().albums.get_compilation_ids([])
                artists = []
            elif App().settings.get_value("show-performers"):
                artists = App().artists.get_all(genre_ids)
                compilations = App().albums.get_compilation_ids(genre_ids)
            else:
                artists = App().artists.get(genre_ids)
                compilations = App().albums.get_compilation_ids(genre_ids)
            return (artists, compilations)

        def setup(artists, compilations):
            mask = SelectionListMask.ARTISTS
            if compilations:
                mask |= SelectionListMask.COMPILATIONS
            selection_list.mark_as(mask)
            items = selection_list.get_headers(selection_list.mask)
            items += artists
            if update:
                selection_list.update_values(items)
            else:
                selection_list.populate(items)
        if selection_list == self._list_one:
            if self._list_two.is_visible():
                self._list_two.hide()
            self._list_two_restore = Type.NONE
        loader = Loader(target=load, view=selection_list,
                        on_finished=lambda r: setup(*r))
        loader.start()

    def __on_list_one_activated(self, listbox, row):
        """
            Update view based on selected object
            @param listbox as Gtk.ListBox
            @param row as Gtk.ListBoxRow
        """
        Logger.debug("Container::__on_list_one_activated()")
        self._stack.destroy_children()
        if App().window.is_adaptive:
            App().window.emit("can-go-back-changed", True)
        else:
            App().window.emit("show-can-go-back", False)
            App().window.emit("can-go-back-changed", False)
        view = None
        selected_ids = self._list_one.selected_ids
        if not selected_ids:
            return
        # Update lists
        if selected_ids[0] in [Type.PLAYLISTS, Type.YEARS] and\
                self._list_one.mask & SelectionListMask.GENRES:
            self.__update_list_playlists(False, selected_ids[0])
            self._list_two.show()
        elif (selected_ids[0] > 0 or selected_ids[0] == Type.ALL) and\
                self._list_one.mask & SelectionListMask.GENRES:
            self.__update_list_artists(self._list_two, selected_ids, False)
            self._list_two.show()
        else:
            self._list_two.hide()
        # Update view
        if selected_ids[0] == Type.PLAYLISTS:
            view = self._get_view_playlists()
        elif selected_ids[0] == Type.CURRENT:
            view = self.get_view_current()
        elif selected_ids[0] == Type.SEARCH:
            view = self.get_view_search()
        elif selected_ids[0] in [Type.POPULARS,
                                 Type.LOVED,
                                 Type.RECENTS,
                                 Type.NEVER,
                                 Type.RANDOMS,
                                 Type.WEB]:
            view = self._get_view_albums(selected_ids, [])
        elif selected_ids[0] == Type.RADIOS:
            view = self._get_view_radios()
        elif selected_ids[0] == Type.YEARS:
            view = self._get_view_albums_decades()
        elif selected_ids[0] == Type.GENRES:
            view = self._get_view_genres()
        elif selected_ids[0] == Type.ARTISTS:
            view = self._get_view_artists_rounded(False)
        elif self._list_one.mask & SelectionListMask.ARTISTS:
            if selected_ids[0] == Type.ALL:
                view = self._get_view_albums(selected_ids, [])
            elif selected_ids[0] == Type.COMPILATIONS:
                view = self._get_view_albums([], selected_ids)
            else:
                view = self._get_view_artists([], selected_ids)
        elif not App().window.is_adaptive:
            view = self._get_view_albums(selected_ids, [])
        if view is not None and view not in self._stack.get_children():
            self._stack.add(view)
        # If we are in paned stack mode, show list two if wanted
        if App().window.is_adaptive\
                and self._list_two.is_visible()\
                and (
                    selected_ids[0] >= 0 or
                    selected_ids[0] == Type.ALL):
            self._stack.set_visible_child(self._list_two)
        elif view is not None:
            self._stack.set_visible_child(view)

    def __on_list_one_populated(self, selection_list):
        """
            @param selection_list as SelectionList
        """
        pass

    def __on_list_two_activated(self, listbox, row):
        """
            Update view based on selected object
            @param listbox as Gtk.ListBox
            @param row as Gtk.ListBoxRow
        """
        Logger.debug("Container::__on_list_two_activated()")
        self._stack.destroy_children()
        if not App().window.is_adaptive:
            App().window.emit("show-can-go-back", False)
            App().window.emit("can-go-back-changed", False)
        genre_ids = self._list_one.selected_ids
        selected_ids = self._list_two.selected_ids
        if not selected_ids or not genre_ids:
            return
        if genre_ids[0] == Type.PLAYLISTS:
            view = self._get_view_playlists(selected_ids)
        elif genre_ids[0] == Type.YEARS:
            view = self._get_view_albums_years(selected_ids)
        elif selected_ids[0] == Type.COMPILATIONS:
            view = self._get_view_albums(genre_ids, selected_ids)
        else:
            view = self._get_view_artists(genre_ids, selected_ids)
        self._stack.add(view)
        self._stack.set_visible_child(view)

    def __on_pass_focus(self, selection_list):
        """
            Pass focus to other list
            @param selection_list as SelectionList
        """
        if selection_list == self._list_one:
            if self._list_two.is_visible():
                self._list_two.grab_focus()
        else:
            self._list_one.grab_focus()

    def __on_list_two_mapped(self, widget):
        """
            Force paned width, see ignore in container.py
        """
        position = App().settings.get_value(
            "paned-listview-width").get_int32()
        GLib.timeout_add(100, self._paned_two.set_position, position)
