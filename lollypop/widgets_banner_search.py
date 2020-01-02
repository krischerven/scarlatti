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

from lollypop.define import App, ArtSize, Type, ViewType
from lollypop.widgets_banner import BannerWidget
from lollypop.logger import Logger


class SearchBannerWidget(BannerWidget):
    """
        Banner for search
    """

    def __init__(self, view):
        """
            Init banner
            @param view as AlbumsListView
        """
        BannerWidget.__init__(self, ViewType.OVERLAY)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SearchBannerWidget.ui")
        self.__view = view
        self.__play_button = builder.get_object("play_button")
        self.__new_button = builder.get_object("new_button")
        self.__spinner = builder.get_object("spinner")
        self.__entry = builder.get_object("entry")
        widget = builder.get_object("widget")
        self._overlay.add_overlay(widget)
        self._overlay.set_overlay_pass_through(widget, True)
        self.connect("map", self.__on_map)
        builder.connect_signals(self)

    def update_for_width(self, width):
        """
            Update banner internals for width, call this before showing banner
            @param width as int
        """
        BannerWidget.update_for_width(self, width)
        self.__entry.set_size_request(self.width / 4, -1)

    @property
    def spinner(self):
        """
            Get banner spinner
            @return Gtk.Spinner
        """
        return self.__spinner

    @property
    def entry(self):
        """
            Get banner entry
            @return Gtk.Entry
        """
        return self.__entry

    @property
    def new_button(self):
        """
            Get new button
            @return Gtk.Button
        """
        return self.__new_button

    @property
    def play_button(self):
        """
            Get play button
            @return Gtk.Button
        """
        return self.__play_button

    @property
    def height(self):
        """
            Get wanted height
            @return int
        """
        return ArtSize.SMALL

#######################
# PROTECTED           #
#######################
    def _handle_width_allocate(self, allocation):
        """
            Update entry width
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_width_allocate(self, allocation):
            self.__entry.set_size_request(self.width / 4, -1)

    def _on_play_button_clicked(self, button):
        """
            Play search
            @param button as Gtk.Button
        """
        try:
            App().player.clear_albums()
            children = self.__view.children
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

#######################
# PRIVATE             #
#######################
    def __search_to_playlist(self):
        """
            Create a new playlist based on search
        """
        current_search = self.__entry.get_text()
        if not current_search:
            return
        tracks = []
        for child in self.__view.children:
            tracks += child.album.tracks
        if tracks:
            playlist_id = App().playlists.get_id(current_search)
            if playlist_id is None:
                playlist_id = App().playlists.add(current_search)
            App().playlists.add_tracks(playlist_id, tracks)
            GLib.idle_add(App().window.container.show_view,
                          [Type.PLAYLISTS], playlist_id)

    def __on_map(self, widget):
        """
            Grab focus
            @param widget as Gtk.Widget
        """
        GLib.idle_add(self.__entry.grab_focus)
