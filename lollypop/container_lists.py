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

from lollypop.logger import Logger
from lollypop.selectionlist import SelectionList
from lollypop.define import App, Type, SelectionListMask
from lollypop.shown import ShownLists


class ListsContainer:
    """
        Selections lists management for main view
    """

    def __init__(self):
        """
            Init container
        """
        pass

    def setup_lists(self):
        """
            Setup container lists
        """
        self._sidebar = SelectionList(SelectionListMask.SIDEBAR)
        self._sidebar.show()
        self._list_view = SelectionList(SelectionListMask.LIST_VIEW)
        self._sidebar.listbox.connect("row-activated",
                                      self.__on_sidebar_activated)
        self._list_view.listbox.connect("row-activated",
                                        self.__on_list_view_activated)
        self._sidebar.connect("populated", self.__on_sidebar_populated)
        self._list_view.connect("map", self.__on_list_view_mapped)

        App().window.add_adaptive_child(self._sidebar_one, self._sidebar)
        App().window.add_adaptive_child(self._sidebar_two, self._list_view)
        self._sidebar.set_mask(SelectionListMask.SIDEBAR)
        items = ShownLists.get(SelectionListMask.SIDEBAR)
        items.append((Type.CURRENT, _("Current playlist"),
                     _("Current playlist")))
        self._sidebar.populate(items)

    @property
    def sidebar(self):
        """
            Get first SelectionList
            @return SelectionList
        """
        return self._sidebar

    @property
    def list_view(self):
        """
            Get second SelectionList
            @return SelectionList
        """
        return self._list_view

##############
# PROTECTED  #
##############

############
# PRIVATE  #
############
    def __show_genres_list(self, selection_list):
        """
            Setup list for genres
            @param list as SelectionList
        """
        def load():
            genres = App().genres.get()
            return genres

        App().task_helper.run(load, callback=(selection_list.populate,))
        selection_list.set_mask(SelectionListMask.GENRES)

    def __show_artists_list(self, selection_list):
        """
            Setup list for artists
            @param list as SelectionList
        """
        def load():
            if App().settings.get_value("show-performers"):
                artists = App().artists.get_all([])
            else:
                artists = App().artists.get([])
            return artists
        App().task_helper.run(load, callback=(selection_list.populate,))
        selection_list.set_mask(SelectionListMask.ARTISTS)

    def __on_sidebar_activated(self, listbox, row):
        """
            Update view based on selected object
            @param listbox as Gtk.ListBox
            @param row as Gtk.ListBoxRow
        """
        Logger.debug("Container::__on_sidebar_activated()")
        view = None
        selected_ids = self._sidebar.selected_ids
        visible = self._stack.get_visible_child()
        if not selected_ids or (visible is not None and
                                visible.sidebar_id != Type.RANDOMS and
                                visible.sidebar_id in selected_ids):
            return
        # Update lists
        if selected_ids[0] == Type.ARTISTS_LIST:
            self.__show_artists_list(self._list_view)
            self._list_view.show()
        elif selected_ids[0] == Type.GENRES_LIST:
            self.__show_genres_list(self._list_view)
            self._list_view.show()
        else:
            self._list_view.hide()

        if selected_ids[0] == Type.PLAYLISTS:
            view = self._get_view_playlists()
        elif selected_ids[0] == Type.LYRICS:
            view = self._get_view_lyrics()
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
            view = self._get_view_artists_rounded()
        elif selected_ids[0] == Type.ALL:
            view = self._get_view_albums(selected_ids, [])
        elif selected_ids[0] == Type.COMPILATIONS:
            view = self._get_view_albums([], selected_ids)
        if view is not None and view not in self._stack.get_children():
            view.show()
            self._stack.add(view)
        # If we are in paned stack mode, show list two if wanted
        if App().window.is_adaptive\
                and self._list_view.get_visible()\
                and selected_ids[0] in [Type.ARTISTS_LIST,
                                        Type.GENRES_LIST]:
            self._stack.set_visible_child(self._list_view)
        elif view is not None:
            self._stack.set_visible_child(view)

    def __on_sidebar_populated(self, selection_list):
        """
            @param selection_list as SelectionList
        """
        if App().settings.get_value("save-state"):
            self._stack.load_history()
            App().window.emit("can-go-back-changed", App().window.can_go_back)
        else:
            startup_id = App().settings.get_value("startup-id").get_int32()
            if startup_id == -1:
                self.show_view([Type.HOME])
            else:
                selection_list.select_ids([startup_id], True)

    def __on_list_view_activated(self, listbox, row):
        """
            Update view based on selected object
            @param listbox as Gtk.ListBox
            @param row as Gtk.ListBoxRow
        """
        Logger.debug("Container::__on_list_view_activated()")
        selected_ids = self._list_view.selected_ids
        if self._list_view.mask & SelectionListMask.GENRES:
            view = self._get_view_albums(selected_ids, [])
        else:
            view = self._get_view_artists([], selected_ids)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)

    def __on_list_view_mapped(self, widget):
        """
            Force paned width, see ignore in container.py
        """
        position = App().settings.get_value(
            "paned-listview-width").get_int32()
        GLib.timeout_add(100, self._sidebar_two.set_position, position)
