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

from gi.repository import Gtk, GObject

from random import choice, shuffle

from lollypop.utils import get_human_duration, tracks_to_albums
from lollypop.objects_track import Track
from lollypop.define import App, ArtSize, ArtBehaviour, MARGIN, ViewType
from lollypop.widgets_banner import BannerWidget


class PlaylistBannerWidget(BannerWidget):
    """
        Banner for playlist
    """

    __gsignals__ = {
        "jump-to-current": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, playlist_id, view):
        """
            Init artist banner
            @param playlist_id as int
            @param view as AlbumsListView
        """
        BannerWidget.__init__(self, view.args[0]["view_type"])
        self.__playlist_id = playlist_id
        self.__view = view
        self.__track = None
        self.__track_ids = []
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/Lollypop/PlaylistBannerWidget.ui")
        self.__title_label = builder.get_object("title")
        self.__duration_label = builder.get_object("duration")
        self.__play_button = builder.get_object("play_button")
        self.__shuffle_button = builder.get_object("shuffle_button")
        self.__jump_button = builder.get_object("jump_button")
        self.__menu_button = builder.get_object("menu_button")
        self.add_overlay(builder.get_object("widget"))
        self.__title_label.set_label(App().playlists.get_name(playlist_id))
        builder.connect_signals(self)
        if App().playlists.get_smart(playlist_id):
            request = App().playlists.get_smart_sql(playlist_id)
            if request is not None:
                self.__track_ids = App().db.execute(request)
        else:
            self.__track_ids = App().playlists.get_track_ids(playlist_id)
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
        def update_button(button, style, icon_size, icon_name):
            context = button.get_style_context()
            context.remove_class("menu-button-48")
            context.remove_class("menu-button")
            context.add_class(style)
            button.get_image().set_from_icon_name(icon_name, icon_size)

        BannerWidget.set_view_type(self, view_type)
        duration_context = self.__duration_label.get_style_context()
        title_context = self.__title_label.get_style_context()
        for c in title_context.list_classes():
            title_context.remove_class(c)
        for c in duration_context.list_classes():
            duration_context.remove_class(c)
        if view_type & ViewType.SMALL:
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
        update_button(self.__jump_button, style,
                      icon_size, "go-jump-symbolic")
        update_button(self.__menu_button, style,
                      icon_size, "view-more-symbolic")

#######################
# PROTECTED           #
#######################
    def _handle_size_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_size_allocate(self, allocation):
            if self.__track_ids and self.__track is None:
                track_id = choice(self.__track_ids)
                self.__track_ids.remove(track_id)
                self.__track = Track(track_id)
            if self.__track is not None:
                App().art_helper.set_album_artwork(
                    self.__track.album,
                    # +100 to prevent resize lag
                    allocation.width + 100,
                    ArtSize.BANNER + MARGIN * 2,
                    self._artwork.get_scale_factor(),
                    ArtBehaviour.BLUR_HARD |
                    ArtBehaviour.DARKER,
                    self.__on_album_artwork)

    def _on_jump_button_clicked(self, button):
        """
            Scroll to current track
            @param button as Gtk.Button
        """
        self.emit("jump-to-current")

    def _on_play_button_clicked(self, button):
        """
            Play playlist
            @param button as Gtk.Button
        """
        tracks = []
        for album_row in self.__view.children:
            for track_row in album_row.children:
                tracks.append(track_row.track)
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
            for track_row in album_row.children:
                tracks.append(track_row.track)
        if tracks:
            shuffle(tracks)
            albums = tracks_to_albums(tracks)
            App().player.play_track_for_albums(tracks[0], albums)

    def _on_menu_button_clicked(self, button):
        """
            Show playlist menu
            @param button as Gtk.Button
        """
        from lollypop.menu_playlist import PlaylistMenu
        menu = PlaylistMenu(self.__playlist_id)
        popover = Gtk.Popover.new_from_model(button, menu)
        popover.popup()

#######################
# PRIVATE             #
#######################
    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is not None:
            self._artwork.set_from_surface(surface)
