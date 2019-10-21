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

from random import shuffle

from lollypop.utils import get_human_duration, tracks_to_albums, update_button
from lollypop.utils import popup_widget
from lollypop.define import App, ArtSize, ViewType
from lollypop.widgets_banner import BannerWidget


class PlaylistBannerWidget(BannerWidget):
    """
        Banner for playlist
    """

    def __init__(self, playlist_id, view):
        """
            Init banner
            @param playlist_id as int
            @param view as AlbumsListView
        """
        BannerWidget.__init__(self, view.args["view_type"] | ViewType.OVERLAY)
        self.__playlist_id = playlist_id
        self.__view = view
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/Lollypop/PlaylistBannerWidget.ui")
        self.__title_label = builder.get_object("title")
        self.__spinner = builder.get_object("spinner")
        self.__duration_label = builder.get_object("duration")
        self.__play_button = builder.get_object("play_button")
        self.__shuffle_button = builder.get_object("shuffle_button")
        self.__menu_button = builder.get_object("menu_button")
        widget = builder.get_object("widget")
        self._overlay.add_overlay(widget)
        self._overlay.set_overlay_pass_through(widget, True)
        self.__title_label.set_label(App().playlists.get_name(playlist_id))
        builder.connect_signals(self)
        # In DB duration calculation
        if playlist_id > 0 and\
                not App().playlists.get_smart(playlist_id):
            duration = App().playlists.get_duration(playlist_id)
            self.__duration_label.set_text(get_human_duration(duration))

    def set_view_type(self, view_type):
        """
            Update view type
            @param view_type as ViewType
        """
        BannerWidget.set_view_type(self, view_type)
        duration_context = self.__duration_label.get_style_context()
        title_context = self.__title_label.get_style_context()
        for c in title_context.list_classes():
            title_context.remove_class(c)
        for c in duration_context.list_classes():
            duration_context.remove_class(c)
        if view_type & ViewType.ADAPTIVE:
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
            title_context.add_class("text-large")
        else:
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            title_context.add_class("text-x-large")
            duration_context.add_class("text-large")
        update_button(self.__play_button, style,
                      icon_size, "media-playback-start-symbolic")
        update_button(self.__shuffle_button, style,
                      icon_size, "media-playlist-shuffle-symbolic")
        update_button(self.__menu_button, style,
                      icon_size, "view-more-symbolic")

    @property
    def spinner(self):
        """
            Get spinner
            @return Gtk.Spinner
        """
        return self.__spinner

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
    def _on_play_button_clicked(self, button):
        """
            Play playlist
            @param button as Gtk.Button
        """
        tracks = []
        for album_row in self.__view.children:
            for track in album_row.album.tracks:
                tracks.append(track)
        if tracks:
            albums = tracks_to_albums(tracks)
            App().player.play_track_for_albums(tracks[0], albums)

    def _on_shuffle_button_clicked(self, button):
        """
            Play playlist shuffled
            @param button as Gtk.Button
        """
        tracks = []
        for album_row in self.__view.children:
            for track in album_row.album.tracks:
                tracks.append(track)
        if tracks:
            shuffle(tracks)
            albums = tracks_to_albums(tracks)
            App().player.play_track_for_albums(tracks[0], albums)

    def _on_menu_button_clicked(self, button):
        """
            Show playlist menu
            @param button as Gtk.Button
        """
        from lollypop.widgets_menu import MenuBuilder
        from lollypop.menu_playlist import PlaylistMenu, PlaylistMenuExt
        menu = PlaylistMenu(self.__playlist_id, App().window.is_adaptive)
        menu_widget = MenuBuilder(menu)
        if self.__playlist_id >= 0:
            menu_widget = MenuBuilder(menu)
            main = menu_widget.get_child_by_name("main")
            menu_ext = PlaylistMenuExt(self.__playlist_id)
            menu_ext.show()
            main.add(menu_ext)
        else:
            menu_widget = MenuBuilder(menu)
        menu_widget.show()
        popup_widget(menu_widget, button)
