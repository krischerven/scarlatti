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

from random import shuffle

from lollypop.utils import get_human_duration, tracks_to_albums
from lollypop.view import LazyLoadingView
from lollypop.define import App, ViewType, MARGIN, Type
from lollypop.objects_album import Album
from lollypop.objects_track import Track
from lollypop.controller_view import ViewController, ViewControllerType
from lollypop.widgets_banner_playlist import PlaylistBannerWidget
from lollypop.view_albums_list import AlbumsListView
from lollypop.logger import Logger
from lollypop.helper_filtering import FilteringHelper
from lollypop.helper_signals import SignalsHelper


class PlaylistsView(LazyLoadingView, ViewController, FilteringHelper,
                    SignalsHelper):
    """
        View showing playlists
    """

    def __init__(self, playlist_ids, view_type):
        """
            Init PlaylistView
            @parma playlist ids as [int]
            @param view_type as ViewType
        """
        self.signals = [
            (App().playlists, "playlist-track-added",
             "_on_playlist_track_added"),
            (App().playlists, "playlist-track-removed",
             "_on_playlist_track_removed")
        ]
        LazyLoadingView.__init__(self, view_type)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        SignalsHelper.__init__(self)
        FilteringHelper.__init__(self)
        self._playlist_ids = playlist_ids
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/PlaylistView.ui")
        self.__title_label = builder.get_object("title")
        self.__duration_label = builder.get_object("duration")
        self.__play_button = builder.get_object("play_button")
        self.__shuffle_button = builder.get_object("shuffle_button")
        self.__jump_button = builder.get_object("jump_button")
        self.__menu_button = builder.get_object("menu_button")
        self.__buttons = builder.get_object("box-buttons")
        self.__widget = builder.get_object("widget")
        # We remove SCROLLED because we want to be the scrolled view
        self._view = AlbumsListView([], [], view_type & ~ViewType.SCROLLED)
        self._view.connect("remove-from-playlist",
                           self.__on_remove_from_playlist)
        self._view.show()
        self.__title_label.set_margin_start(MARGIN)
        self.__buttons.set_margin_end(MARGIN)
        self.__duration_label.set_margin_start(MARGIN)
        self._overlay = Gtk.Overlay.new()
        if view_type & ViewType.SCROLLED:
            self._viewport.add(self._view)
            self._overlay.add(self._scrolled)
        else:
            self._overlay.add(self._view)
        self._overlay.show()
        self.__widget.attach(self.__title_label, 0, 0, 1, 1)
        self.__widget.attach(self.__duration_label, 0, 1, 1, 1)
        self.__widget.attach(self.__buttons, 1, 0, 1, 2)
        self.__widget.set_vexpand(True)
        self.__title_label.set_vexpand(True)
        self.__duration_label.set_vexpand(True)
        self.__title_label.set_property("valign", Gtk.Align.END)
        self.__duration_label.set_property("valign", Gtk.Align.START)
        self.__banner = PlaylistBannerWidget(playlist_ids[0], view_type)
        self.__banner.init_background()
        self.__banner.show()
        self._overlay.add_overlay(self.__banner)
        self.__banner.add_overlay(self.__widget)
        self._view.set_margin_top(self.__banner.height)
        self.add(self._overlay)
        self.__title_label.set_label(
            ", ".join(App().playlists.get_names(playlist_ids)))
        builder.connect_signals(self)

        if len(playlist_ids) > 1:
            self.__menu_button.hide()

        self.set_view_type(view_type)

        # In DB duration calculation
        if playlist_ids[0] > 0 and\
                not App().playlists.get_smart(playlist_ids[0]):
            duration = 0
            for playlist_id in self._playlist_ids:
                duration += App().playlists.get_duration(playlist_id)
            self.__set_duration(duration)
        # Ask widget after populated
        else:
            self._view.connect("populated", self.__on_playlist_populated)

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

        self.__banner.set_view_type(view_type)
        self._view.set_margin_top(self.__banner.height)
        self._view_type = view_type
        if view_type & ViewType.SMALL:
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
            self.__title_label.get_style_context().add_class(
                "text-x-large")
            self.__duration_label.get_style_context().add_class(
                "text-large")
        else:
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            self.__title_label.get_style_context().add_class(
                "text-xx-large")
            self.__duration_label.get_style_context().add_class(
                "text-x-large")
        update_button(self.__play_button, style,
                      icon_size, "media-playback-start-symbolic")
        update_button(self.__shuffle_button, style,
                      icon_size, "media-playlist-shuffle-symbolic")
        update_button(self.__jump_button, style,
                      icon_size, "go-jump-symbolic")
        update_button(self.__menu_button, style,
                      icon_size, "view-more-symbolic")

    def populate(self):
        """
            Populate view
        """
        def load():
            track_ids = []
            for playlist_id in self._playlist_ids:
                if playlist_id == Type.LOVED:
                    for track_id in App().tracks.get_loved_track_ids():
                        if track_id not in track_ids:
                            track_ids.append(track_id)
                else:
                    for track_id in App().playlists.get_track_ids(playlist_id):
                        if track_id not in track_ids:
                            track_ids.append(track_id)
            return tracks_to_albums(
                [Track(track_id) for track_id in track_ids])

        App().task_helper.run(load, callback=(self._view.populate,))

    def stop(self):
        """
            Stop populating
        """
        self._view.stop()

    def activate_child(self):
        """
            Activated typeahead row
        """
        try:
            if App().player.is_party:
                App().lookup_action("party").change_state(
                    GLib.Variant("b", False))
            for child in self.filtered:
                style_context = child.get_style_context()
                if style_context.has_class("typeahead"):
                    if hasattr(child, "album"):
                        App().player.play_album(child.album)
                    else:
                        track = child.track
                        App().player.add_album(track.album)
                        App().player.load(track.album.get_track(track.id))
                style_context.remove_class("typeahead")
        except Exception as e:
            Logger.error("PlaylistsView::activate_child: %s" % e)

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        view_type = self._view_type & ~self.view_sizing_mask
        return ({"playlist_ids": self._playlist_ids,
                 "view_type": view_type}, self._sidebar_id, position)

    @property
    def filtered(self):
        """
            Get filtered children
            @return [Gtk.Widget]
        """
        filtered = []
        for child in self._view.children:
            filtered.append(child)
            for subchild in child.children:
                filtered.append(subchild)
        return filtered

    @property
    def scroll_shift(self):
        """
            Add scroll shift on y axes
            @return int
        """
        return self.__banner.height + MARGIN

    @property
    def scroll_relative_to(self):
        """
            Relative to scrolled widget
            @return Gtk.Widget
        """
        return self._view

    @property
    def playlist_ids(self):
        """
            Return playlist ids
            @return id as [int]
        """
        return self._playlist_ids

#######################
# PROTECTED           #
#######################
    def _on_value_changed(self, adj):
        """
            Adapt widget to current scroll value
            @param adj as Gtk.Adjustment
        """
        LazyLoadingView._on_value_changed(self, adj)
        if not self._view_type & (ViewType.POPOVER | ViewType.FULLSCREEN):
            title_style_context = self.__title_label.get_style_context()
            if adj.get_value() == adj.get_lower():
                self.__banner.collapse(False)
                self.__duration_label.show()
                self.__title_label.set_property("valign", Gtk.Align.END)
                if not App().window.is_adaptive:
                    title_style_context.remove_class("text-x-large")
                    title_style_context.add_class("text-xx-large")
            else:
                self.__banner.collapse(True)
                self.__duration_label.hide()
                title_style_context.remove_class("text-xx-large")
                title_style_context.add_class("text-x-large")
                self.__title_label.set_property("valign", Gtk.Align.CENTER)

    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        self.__update_jump_button()

    def _on_jump_button_clicked(self, button):
        """
            Scroll to current track
            @param button as Gtk.Button
        """
        self._view.jump_to_current(self._scrolled)

    def _on_play_button_clicked(self, button):
        """
            Play playlist
            @param button as Gtk.Button
        """
        tracks = []
        for album_row in self._view.children:
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
        for album_row in self._view.children:
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
        menu = PlaylistMenu(self._playlist_ids[0])
        popover = Gtk.Popover.new_from_model(button, menu)
        popover.popup()

    def _on_adaptive_changed(self, window, status):
        """
            Update banner style
            @param window as Window
            @param status as bool
        """
        LazyLoadingView._on_adaptive_changed(self, window, status)
        self.set_view_type(self._view_type)

    def _on_playlist_track_added(self, playlists, playlist_id, uri):
        """
            Append track to album list
            @param playlists as Playlists
            @param playlist_id as int
            @param uri as str
        """
        if len(self._playlist_ids) == 1 and\
                playlist_id in self._playlist_ids:
            track = Track(App().tracks.get_id_by_uri(uri))
            album = Album(track.album.id)
            album.set_tracks([track])
            self._view.insert_album(album, True, -1)

    def _on_playlist_track_removed(self, playlists, playlist_id, uri):
        """
            Remove track from album list
            @param playlists as Playlists
            @param playlist_id as int
            @param uri as str
        """
        if len(self._playlist_ids) == 1 and\
                playlist_id in self._playlist_ids:
            track = Track(App().tracks.get_id_by_uri(uri))
            children = self._view.children
            for album_row in children:
                if album_row.album.id == track.album.id:
                    for track_row in album_row.children:
                        if track_row.track.id == track.id:
                            track_row.destroy()
                            if len(children) == 1:
                                album_row.destroy()
                                break

#######################
# PRIVATE             #
#######################
    def __set_duration(self, duration):
        """
            Set playlist duration
            @param duration as int (seconds)
        """
        self.__duration_label.set_text(get_human_duration(duration))

    def __update_jump_button(self):
        """
            Update jump button status
        """
        track_ids = []
        for child in self._view.children:
            track_ids += child.album.track_ids
        if App().player.current_track.id in track_ids:
            self.__jump_button.set_sensitive(True)
        else:
            self.__jump_button.set_sensitive(False)

    def __on_populated(self, playlists_widget):
        """
            Update jump button on populated
            @param playlists_widget as PlaylistsWidget
        """
        self.__update_jump_button()

    def __on_remove_from_playlist(self, view, object):
        """
            Remove object from playlist
            @param view as AlbumListView
            @param object as Album/Track
        """
        if isinstance(object, Album):
            tracks = object.tracks
        else:
            tracks = [object]
        App().playlists.remove_tracks(self._playlist_ids[0], tracks)

    def __on_playlist_populated(self, widget):
        """
            Set duration on populated
            @param widget as PlaylistsWidget
        """
        self.__set_duration(widget.duration)


class SmartPlaylistsView(PlaylistsView):
    """
        View showing smart playlists
    """

    def __init__(self, playlist_ids, view_type):
        """
            Init PlaylistView
            @parma playlist ids as [int]
            @param view_type as ViewType
        """
        PlaylistsView.__init__(self, playlist_ids, view_type)

    def populate(self):
        """
            Populate view
        """
        def load():
            request = App().playlists.get_smart_sql(self._playlist_ids[0])
            track_ids = App().db.execute(request)
            return tracks_to_albums(
                [Track(track_id) for track_id in track_ids])

        App().task_helper.run(load, callback=(self._view.populate,))
