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

from gettext import gettext as _
from random import choice

from lollypop.utils import set_cursor_type, on_query_tooltip
from lollypop.utils_artists import add_artist_to_playback, play_artists
from lollypop.define import App, ArtSize, ArtBehaviour, ViewType, MARGIN, Size
from lollypop.widgets_banner import BannerWidget
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.helper_size_allocation import SizeAllocationHelper


class ArtistBannerWidget(BannerWidget, SignalsHelper):
    """
        Banner for artist
    """

    @signals_map
    def __init__(self, genre_ids, artist_ids, view_type=ViewType.DEFAULT):
        """
            Init artist banner
            @parma genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType (Unused)
        """
        BannerWidget.__init__(self, view_type)
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtistBannerWidget.ui")
        builder.connect_signals(self)
        self.__badge_artwork = builder.get_object("badge_artwork")
        self.__title_label = builder.get_object("artist")
        self.__title_label.connect("realize", set_cursor_type)
        self.__title_label.connect("query-tooltip", on_query_tooltip)
        self.__title_label.set_property("has-tooltip", True)
        self.__add_button = builder.get_object("add_button")
        self.__play_button = builder.get_object("play_button")
        self.__lastfm_button = builder.get_object("lastfm_button")
        builder.get_object("buttons").set_margin_end(MARGIN)
        builder.get_object("artwork_event").connect(
            "realize", set_cursor_type)
        builder.get_object("label_event").connect(
            "realize", set_cursor_type)
        widget = builder.get_object("widget")
        artists = []
        for artist_id in self.__artist_ids:
            artists.append(App().artists.get_name(artist_id))
        self.__title_label.set_markup(
            GLib.markup_escape_text(", ".join(artists)))
        self.__show_artwork = len(artist_ids) == 1
        self.__title_label.get_style_context().add_class("text-x-large")
        self._overlay.add_overlay(widget)
        self._overlay.set_overlay_pass_through(widget, True)
        self.__update_add_button()
        return [
               (App().art, "artist-artwork-changed",
                "_on_artist_artwork_changed"),
               (App().player, "playback-changed", "_on_playback_changed"),
               (App().settings, "changed::artist-artwork",
                "_on_artist_artwork_setting_changed")

        ]

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        BannerWidget.set_view_type(self, view_type)
        art_size = 0
        if view_type & ViewType.MEDIUM:
            art_size = ArtSize.MEDIUM
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
            self.__title_label.get_style_context().add_class(
                "text-large")
        else:
            art_size = ArtSize.BANNER
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            self.__title_label.get_style_context().add_class(
                "text-xx-large")
        self.__set_badge_artwork(art_size)
        for (button, icon_name) in [
                (self.__play_button, "media-playback-start-symbolic"),
                (self.__add_button, "list-add-symbolic"),
                (self.__lastfm_button, "system-users-symbolic")]:
            button_style_context = button.get_style_context()
            button_style_context.remove_class("menu-button-48")
            button_style_context.remove_class("menu-button")
            button_style_context.add_class(style)
            button.get_image().set_from_icon_name(icon_name, icon_size)
        self.__set_text_height()

#######################
# PROTECTED           #
#######################
    def _handle_width_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if SizeAllocationHelper._handle_width_allocate(self, allocation):
            self.__set_artwork()
            if allocation.width >= Size.SMALL + 100:
                self.__badge_artwork.show()
            else:
                self.__badge_artwork.hide()

    def _on_artist_artwork_setting_changed(self, settings, variant):
        """
            Update banner
            @param settings as Gio.Settings
            @param value as GLib.Variant
        """
        self.__set_artwork()
        self.set_view_type(self._view_type)

    def _on_label_button_release(self, eventbox, event):
        """
            Show artists information
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if len(self.__artist_ids) == 1:
            from lollypop.pop_information import InformationPopover
            self.__pop_info = InformationPopover(True)
            self.__pop_info.set_relative_to(eventbox)
            self.__pop_info.populate(self.__artist_ids[0])
            self.__pop_info.show()

    def _on_play_clicked(self, *ignore):
        """
            Play artist albums
        """
        play_artists(self.__artist_ids, self.__genre_ids)
        self.__update_add_button()

    def _on_add_clicked(self, *ignore):
        """
            Add artist albums
        """
        icon_name = self.__add_button.get_image().get_icon_name()[0]
        add = icon_name == "list-add-symbolic"
        add_artist_to_playback(self.__artist_ids, self.__genre_ids, add)
        self.__update_add_button()

    def _on_similars_button_toggled(self, button):
        """
            Show similar artists
            @param button as Gtk.Button
        """
        if button.get_active():
            from lollypop.pop_similars import SimilarsPopover
            popover = SimilarsPopover()
            popover.set_relative_to(button)
            popover.populate(self.__artist_ids)
            popover.connect("closed", lambda x: button.set_active(False))
            popover.popup()

    def _on_badge_button_release(self, eventbox, event):
        """
            Show artist artwork manager
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        from lollypop.pop_artwork import ArtworkPopover
        pop = ArtworkPopover(self.__artist_ids[0])
        pop.set_relative_to(eventbox)
        pop.show()

    def _on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        if len(self.__artist_ids) == 1:
            artist = App().artists.get_name(self.__artist_ids[0])
            if prefix == artist:
                self.__set_artwork()
                self.set_view_type(self._view_type)

    def _on_playback_changed(self, player):
        """
            Update add button
            @param player as Player
        """
        self.__update_add_button()

#######################
# PRIVATE             #
#######################
    def __set_artwork(self):
        """
            Set artwork
        """
        if App().settings.get_value("artist-artwork"):
            artist = App().artists.get_name(choice(self.__artist_ids))
            App().art_helper.set_artist_artwork(
                                        artist,
                                        # +100 to prevent resize lag
                                        self.get_allocated_width() + 100,
                                        self.height,
                                        self.get_scale_factor(),
                                        ArtBehaviour.BLUR_HARD |
                                        ArtBehaviour.DARKER,
                                        self._on_artwork)
        else:
            self._set_default_background()

    def __set_badge_artwork(self, art_size):
        """
            Set artist artwork on badge
            @param art_size as int
        """
        if self.__show_artwork and\
                App().settings.get_value("artist-artwork"):
            self.__badge_artwork.set_margin_start(MARGIN)
            self.__title_label.set_margin_start(0)
            artist = App().artists.get_name(self.__artist_ids[0])
            App().art_helper.set_artist_artwork(
                                        artist,
                                        art_size,
                                        art_size,
                                        self.get_scale_factor(),
                                        ArtBehaviour.ROUNDED |
                                        ArtBehaviour.CROP_SQUARE |
                                        ArtBehaviour.CACHE,
                                        self.__on_badge_artist_artwork,
                                        art_size)
        else:
            self.__badge_artwork.hide()
            self.__badge_artwork.set_margin_start(0)
            self.__title_label.set_margin_start(MARGIN)

    def __set_text_height(self):
        """
            Set text height
        """
        title_context = self.__title_label.get_style_context()
        for c in title_context.list_classes():
            title_context.remove_class(c)
        if self._view_type & (ViewType.MEDIUM | ViewType.SMALL):
            self.__title_label.get_style_context().add_class(
                "text-x-large")
        else:
            self.__title_label.get_style_context().add_class(
                "text-xx-large")

    def __update_add_button(self):
        """
            Set image as +/-
        """
        album_ids = App().albums.get_ids(self.__artist_ids, self.__genre_ids)
        add = set(App().player.album_ids) & set(album_ids) != set(album_ids)
        (name, pixel_size) = self.__add_button.get_image().get_icon_name()
        if add:
            # Translators: artist context
            self.__add_button.set_tooltip_text(_("Add to current playlist"))
            self.__add_button.get_image().set_from_icon_name(
                "list-add-symbolic",
                pixel_size)
        else:
            # Translators: artist context
            self.__add_button.set_tooltip_text(
                _("Remove from current playlist"))
            self.__add_button.get_image().set_from_icon_name(
                "list-remove-symbolic",
                pixel_size)

    def __on_badge_artist_artwork(self, surface, art_size):
        """
            Set artist artwork on badge
            @param surface as cairo.Surface
            @param art_size as int
        """
        if self.get_allocated_width() >= Size.SMALL + 100:
            self.__badge_artwork.show()
        if surface is None:
            self.__badge_artwork.get_style_context().add_class("artwork-icon")
            self.__badge_artwork.set_size_request(art_size, art_size)
            self.__badge_artwork.set_from_icon_name(
                                              "avatar-default-symbolic",
                                              Gtk.IconSize.DIALOG)
        else:
            self.__badge_artwork.get_style_context().remove_class(
                "artwork-icon")
            self.__badge_artwork.set_from_surface(surface)
