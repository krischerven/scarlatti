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

from lollypop.define import App, ArtSize, MARGIN, Type, ViewType, Size
from lollypop.define import ArtBehaviour
from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.widgets_cover import CoverWidget
from lollypop.widgets_banner import BannerWidget
from lollypop.utils import get_human_duration, on_query_tooltip
from lollypop.utils import set_cursor_type, popup_widget
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.helper_gestures import GesturesHelper


class AlbumBannerWidget(BannerWidget, SignalsHelper):
    """
        Banner for album
    """

    @signals_map
    def __init__(self, album, view_type=ViewType.DEFAULT):
        """
            Init cover widget
            @param album
            @param view_type as ViewType
        """
        BannerWidget.__init__(self, view_type)
        self.__cloud_image = None
        self.__album = album
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AlbumBannerWidget.ui")
        builder.connect_signals(self)
        self.__title_label = builder.get_object("title_label")
        self.__title_label.connect("query-tooltip", on_query_tooltip)
        self.__artist_label = builder.get_object("artist_label")
        self.__artist_label.connect("query-tooltip", on_query_tooltip)
        self.__year_label = builder.get_object("year_label")
        self.__duration_label = builder.get_object("duration_label")
        self.__play_button = builder.get_object("play_button")
        self.__add_button = builder.get_object("add_button")
        self.__menu_button = builder.get_object("menu_button")
        if view_type & ViewType.OVERLAY:
            style = "banner-button"
        else:
            style = "menu-button"
        self.__play_button.get_style_context().add_class(style)
        self.__add_button.get_style_context().add_class(style)
        self.__menu_button.get_style_context().add_class(style)
        self.__cover_widget = CoverWidget(album, view_type)
        self.__cover_widget.show()
        self.__title_label.set_label(album.name)
        if view_type & ViewType.ALBUM:
            self.__artist_label.show()
            self.__artist_label.set_label(", ".join(album.artists))
        if album.year is not None:
            self.__year_label.set_label(str(album.year))
            self.__year_label.show()
        duration = App().albums.get_duration(self.__album.id,
                                             self.__album.genre_ids)
        human_duration = get_human_duration(duration)
        self.__duration_label.set_text(human_duration)
        info_eventbox = builder.get_object("info_eventbox")
        info_eventbox.connect("realize", set_cursor_type)
        self.__gesture = GesturesHelper(
            info_eventbox, primary_press_callback=self._on_year_press)
        self.__widget = builder.get_object("widget")
        self.__widget.attach(self.__cover_widget, 0, 0, 1, 3)
        self.__bottom_box = builder.get_object("bottom_box")
        self.__loved_widget = LovedWidget(album, Gtk.IconSize.INVALID)
        self.__loved_widget.show()
        self.__bottom_box.pack_start(self.__loved_widget, 0, False, False)
        self.__rating_widget = RatingWidget(album, Gtk.IconSize.INVALID)
        self.__rating_widget.show()
        self.__bottom_box.pack_start(self.__rating_widget, 0, True, True)
        self.__cover_widget.set_margin_start(MARGIN)
        self.__rating_widget.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)
        self.__loved_widget.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)
        if view_type & ViewType.OVERLAY:
            self._overlay.add_overlay(self.__widget)
            self._overlay.set_overlay_pass_through(self.__widget, True)
        else:
            self.add(self.__widget)
        self.__update_add_button()
        return [
                (App().art, "album-artwork-changed",
                 "_on_album_artwork_changed"),
                (App().player, "playback-changed", "_on_playback_changed")
        ]

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        BannerWidget.set_view_type(self, view_type)
        self.__cover_widget.set_view_type(view_type)
        self.__set_text_height(False)

    def set_selected(self, selected):
        """
            Mark widget as selected
            @param selected as bool
        """
        if selected:
            self.__widget.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self.__widget.set_state_flags(Gtk.StateFlags.NORMAL, True)

#######################
# PROTECTED           #
#######################
    def _handle_width_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_width_allocate(self, allocation):
            if self._view_type & ViewType.ALBUM:
                App().art_helper.set_album_artwork(
                        self.__album,
                        # +100 to prevent resize lag
                        allocation.width + 100,
                        ArtSize.BANNER + MARGIN * 2,
                        self._artwork.get_scale_factor(),
                        ArtBehaviour.BLUR_HARD |
                        ArtBehaviour.DARKER,
                        self._on_artwork)
            self.__set_text_height(allocation.width < Size.MEDIUM)
            if allocation.width < Size.SMALL + 100:
                self.__cover_widget.hide()
            else:
                self.__cover_widget.show()

    def _on_menu_button_clicked(self, button):
        """
            Show album menu
            @param button as Gtk.Button
        """
        from lollypop.widgets_menu import MenuBuilder
        from lollypop.menu_objects import AlbumMenu
        menu = AlbumMenu(self.__album, self._view_type | ViewType.BANNER,
                         App().window.is_adaptive)
        menu_widget = MenuBuilder(menu)
        menu_widget.show()
        popup_widget(menu_widget, button)

    def _on_play_button_clicked(self, button):
        """
            Play album
           @param button as Gtk.Button
        """
        App().player.play_album(self.__album)

    def _on_add_button_clicked(self, button):
        """
            Add/Remove album
           @param button as Gtk.Button
        """
        if self.__album.id in App().player.album_ids:
            App().player.remove_album_by_id(self.__album.id)
        else:
            App().player.add_album(self.__album)

    def _on_album_artwork_changed(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album_id as int
        """
        if album_id == self.__album.id and\
                self._view_type & ViewType.ALBUM and\
                App().animations:
            App().art_helper.set_album_artwork(
                            self.__album,
                            # +100 to prevent resize lag
                            self.get_allocated_width() + 100,
                            self.height,
                            self._artwork.get_scale_factor(),
                            ArtBehaviour.BLUR_HARD |
                            ArtBehaviour.DARKER,
                            self._on_artwork)

    def _on_playback_changed(self, player):
        """
            Update add button
            @param player as Player
        """
        self.__update_add_button()

    def _on_year_press(self, x, y, event):
        """
            Show years view
            @param x as int
            @param y as int
            @param event as Gdk.EventButton
        """
        App().window.container.show_view([Type.YEARS], [self.__album.year])

#######################
# PRIVATE             #
#######################
    def __update_add_button(self):
        """
            Set image as +/-
        """
        if self.__album.id in App().player.album_ids:
            self.__add_button.get_image().set_from_icon_name(
                "list-remove-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        else:
            self.__add_button.get_image().set_from_icon_name(
                "list-add-symbolic", Gtk.IconSize.LARGE_TOOLBAR)

    def __set_text_height(self, small):
        """
            Set text height base on current view_type or small
            @param small as bool
        """
        title_context = self.__title_label.get_style_context()
        artist_context = self.__artist_label.get_style_context()
        year_context = self.__year_label.get_style_context()
        duration_context = self.__duration_label.get_style_context()
        title_context.remove_class("text-xx-large")
        title_context.remove_class("text-x-large")
        artist_context.remove_class("text-xx-large")
        artist_context.remove_class("text-x-large")
        year_context.remove_class("text-x-large")
        year_context.remove_class("text-medium")
        duration_context.remove_class("text-x-large")
        duration_context.remove_class("text-medium")
        if small or self._view_type & (ViewType.ADAPTIVE | ViewType.SMALL) or\
                not self._view_type & ViewType.OVERLAY:
            title_context.add_class("text-x-large")
            artist_context.add_class("text-x-large")
            year_context.add_class("text-medium")
            duration_context.add_class("text-medium")
        else:
            title_context.add_class("text-xx-large")
            artist_context.add_class("text-xx-large")
            year_context.add_class("text-x-large")
            duration_context.add_class("text-x-large")
