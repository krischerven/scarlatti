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


class PlaylistsContainer:
    """
        Playlists management for main view
    """

    def __init__(self):
        """
            Init container
        """
        App().playlists.connect("playlists-changed", self.__update_playlists)

    def show_playlist_manager(self, obj):
        """
            Show playlist manager for object_id
            Current view stay present in ViewContainer
            @param obj as Track/Album
        """
        from lollypop.view_playlists_manager import PlaylistsManagerView
        current = self._stack.get_visible_child()
        view = PlaylistsManagerView(obj, ViewType.SCROLLED)
        view.populate(App().playlists.get_ids())
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        current.disable_overlay()

    def show_smart_playlist_editor(self, playlist_id):
        """
            Show a view allowing user to edit smart view
            @param playlist_id as int
        """
        from lollypop.view_playlist_smart import SmartPlaylistView
        current = self._stack.get_visible_child()
        view = SmartPlaylistView(playlist_id)
        view.populate()
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        current.disable_overlay()

##############
# PROTECTED  #
##############

############
# PRIVATE  #
############
    def __update_playlists(self, playlists, playlist_id):
        """
            Update playlists in second list
            @param playlists as Playlists
            @param playlist_id as int
        """
        ids = self._list_one.selected_ids
        if ids and ids[0] == Type.PLAYLISTS:
            if App().playlists.exists(playlist_id):
                self._list_two.update_value(playlist_id,
                                            App().playlists.get_name(
                                                 playlist_id))
            else:
                self._list_two.remove_value(playlist_id)
