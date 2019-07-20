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

from gi.repository import Gdk, Gtk, GLib

from gettext import gettext as _
from random import shuffle, choice

from lollypop.objects_album import Album
from lollypop.utils import on_realize, on_query_tooltip
from lollypop.define import App, ArtSize, ArtBehaviour, ViewType, MARGIN
from lollypop.widgets_banner import BannerWidget
from lollypop.logger import Logger


class ArtistBannerWidget(BannerWidget):
    """
        Banner for artist
    """

    def __init__(self, genre_ids, artist_ids, view_type=ViewType.DEFAULT):
        """
            Init artist banner
            @parma genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType (Unused)
        """
        BannerWidget.__init__(self, view_type)
        self.__album_ids = None
        self.__album_id = None
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtistBannerWidget.ui")
        builder.connect_signals(self)
        self.__badge_artwork = builder.get_object("badge_artwork")
        self.__title_label = builder.get_object("artist")
        self.__title_label.connect("realize", on_realize)
        self.__title_label.connect("query-tooltip", on_query_tooltip)
        self.__title_label.set_property("has-tooltip", True)
        self.__add_button = builder.get_object("add_button")
        self.__play_button = builder.get_object("play_button")
        self.__jump_button = builder.get_object("jump_button")
        self.__lastfm_button = builder.get_object("lastfm_button")
        builder.get_object("buttons").set_margin_end(MARGIN)
        builder.get_object("artwork_event").connect("realize", on_realize)
        builder.get_object("label_event").connect("realize", on_realize)
        widget = builder.get_object("widget")
        self.connect("destroy", self.__on_destroy)
        artists = []
        for artist_id in self.__artist_ids:
            artists.append(App().artists.get_name(artist_id))
        self.__title_label.set_markup(
            GLib.markup_escape_text(", ".join(artists)))
        self.__show_artwork = len(artist_ids) == 1 and\
            App().settings.get_value("artist-artwork")
        if self.__show_artwork:
            self.__title_label.get_style_context().add_class("text-xx-large")
        else:
            self.__title_label.get_style_context().add_class("text-x-large")
        self.__art_signal_id = App().art.connect(
                                           "artist-artwork-changed",
                                           self.__on_artist_artwork_changed)
        self.add_overlay(widget)
        self.set_view_type(view_type)

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        BannerWidget.set_view_type(self, view_type)
        art_size = 0
        if view_type & ViewType.SMALL:
            art_size = ArtSize.MEDIUM
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
            self.__title_label.get_style_context().add_class(
                "text-large")
        elif view_type & ViewType.MEDIUM:
            art_size = ArtSize.BANNER
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            self.__title_label.get_style_context().add_class(
                "text-x-large")
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
                (self.__jump_button, "go-jump-symbolic"),
                (self.__lastfm_button, "system-users-symbolic")]:
            button_style_context = button.get_style_context()
            button_style_context.remove_class("menu-button-48")
            button_style_context.remove_class("menu-button")
            button_style_context.add_class(style)
            button.get_image().set_from_icon_name(icon_name, icon_size)
        self.__set_text_height(self._collapsed)

    def collapse(self, collapsed):
        """
            Collapse banner
            @param collapse as bool
        """
        BannerWidget.collapse(self, collapsed)
        self.__set_text_height(collapsed)
        if collapsed:
            self.__badge_artwork.hide()
        else:
            self.__badge_artwork.show()

#######################
# PROTECTED           #
#######################
    def _handle_size_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_size_allocate(self, allocation):
            if App().settings.get_value("artist-artwork"):
                artist = App().artists.get_name(choice(self.__artist_ids))
                App().art_helper.set_artist_artwork(
                                            artist,
                                            # +100 to prevent resize lag
                                            allocation.width + 100,
                                            ArtSize.BANNER + MARGIN * 2,
                                            self.get_scale_factor(),
                                            ArtBehaviour.BLUR_HARD |
                                            ArtBehaviour.DARKER,
                                            self.__on_artist_artwork)
            else:
                self.__use_album_artwork(allocation.width,
                                         ArtSize.BANNER + MARGIN * 2)

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
        try:
            if App().player.is_party:
                App().lookup_action("party").change_state(
                    GLib.Variant("b", False))
            album_ids = App().albums.get_ids(self.__artist_ids,
                                             self.__genre_ids)
            albums = [Album(album_id) for album_id in album_ids]
            App().player.play_albums(albums)
            self.__update_add_icon(False)
        except Exception as e:
            Logger.error("ArtistView::_on_play_clicked: %s" % e)

    def _on_add_clicked(self, *ignore):
        """
            Add artist albums
        """
        try:
            if App().settings.get_value("show-performers"):
                album_ids = App().tracks.get_album_ids(self.__artist_ids,
                                                       self.__genre_ids)
            else:
                album_ids = App().albums.get_ids(self.__artist_ids,
                                                 self.__genre_ids)
            icon_name = self.__add_button.get_image().get_icon_name()[0]
            add = icon_name == "list-add-symbolic"
            for album_id in album_ids:
                if add and album_id not in App().player.album_ids:
                    App().player.add_album(Album(album_id,
                                                 self.__genre_ids,
                                                 self.__artist_ids))
                elif not add and album_id in App().player.album_ids:
                    App().player.remove_album_by_id(album_id)
            if len(App().player.album_ids) == 0:
                App().player.stop()
            elif App().player.current_track.album.id\
                    not in App().player.album_ids:
                App().player.skip_album()
            self.__update_add_icon(not add)
        except Exception as e:
            Logger.error("ArtistView::_on_add_clicked: %s" % e)

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

    def _on_jump_button_clicked(self, button):
        """
            Scroll to album
            @parma button as Gtk.Button
        """
        widget = None
        for child in self._album_box.get_children():
            if child.album.id == App().player.current_track.album.id:
                widget = child
                break
        if widget is not None:
            y = widget.get_current_ordinate(self._album_box)
            self._scrolled.get_vadjustment().set_value(y)

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

#######################
# PRIVATE             #
#######################
    def __set_badge_artwork(self, art_size):
        """
            Set artist artwork on badge
            @param art_size as int
        """
        if self.__show_artwork:
            self.__badge_artwork.set_margin_start(MARGIN)
            artist = App().artists.get_name(self.__artist_ids[0])
            App().art_helper.set_artist_artwork(
                                        artist,
                                        art_size,
                                        art_size,
                                        self.get_scale_factor(),
                                        ArtBehaviour.ROUNDED |
                                        ArtBehaviour.CROP_SQUARE |
                                        ArtBehaviour.CACHE,
                                        self.__on_badge_artist_artwork)
        else:
            self.__title_label.set_margin_start(MARGIN)
            self.collapse(True)

    def __set_text_height(self, collapsed):
        """
            Set text height
            @param collapsed as bool
        """
        title_context = self.__title_label.get_style_context()
        for c in title_context.list_classes():
            title_context.remove_class(c)
        if collapsed:
            self.__title_label.get_style_context().add_class(
                "text-large")
        elif self._view_type & (ViewType.MEDIUM | ViewType.SMALL):
            self.__title_label.get_style_context().add_class(
                "text-x-large")
        else:
            self.__title_label.get_style_context().add_class(
                "text-xx-large")

    def __update_add_icon(self, add):
        """
            Set icon for Artist +/-
            @param add as bool
        """
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

    def __use_album_artwork(self, width, height):
        """
            Set artwork with album artwork
            @param width as int
            @param height as int
        """
        # Select an album
        if self.__album_id is None:
            if self.__album_ids is None:
                if App().settings.get_value("show-performers"):
                    self.__album_ids = App().tracks.get_album_ids(
                        [self.__artist_id], [])
                else:
                    self.__album_ids = App().albums.get_ids(
                        [self.__artist_id], [])
                shuffle(self.__album_ids)
            if self.__album_ids:
                self.__album_id = self.__album_ids.pop(0)
        # Get artwork
        if self.__album_id is not None:
            album = Album(self.__album_id)
            App().art_helper.set_album_artwork(
                album,
                # +100 to prevent resize lag
                width + 100,
                height,
                self._artwork.get_scale_factor(),
                ArtBehaviour.BLUR_HARD |
                ArtBehaviour.DARKER,
                self.__on_album_artwork)

    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self.__art_signal_id is not None:
            App().art.disconnect(self.__art_signal_id)

    def __on_artist_artwork_changed(self, art, prefix):
        """
            Update artwork if needed
            @param art as Art
            @param prefix as str
        """
        if len(self.__artist_ids) == 1:
            artist = App().artists.get_name(self.__artist_ids[0])
            if prefix == artist:
                rect = Gdk.Rectangle()
                rect.width = self.get_allocated_width()
                rect.height = self.get_allocated_height()
                self.__width = 0
                self.__handle_size_allocate(rect)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is None:
            self.__album_id = None
            self.__use_album_artwork(self.get_allocated_width(),
                                     self.get_allocated_height())
        else:
            self._artwork.set_from_surface(surface)

    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as str
        """
        if surface is None:
            self.__use_album_artwork(self.get_allocated_width(),
                                     self.get_allocated_height())
        else:
            self._artwork.set_from_surface(surface)

    def __on_badge_artist_artwork(self, surface):
        """
            Set artist artwork on badge
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__badge_artwork.get_style_context().add_class("artwork-icon")
            self.__badge_artwork.set_size_request(ArtSize.BANNER,
                                                  ArtSize.BANNER)
            self.__badge_artwork.set_from_icon_name(
                                              "avatar-default-symbolic",
                                              Gtk.IconSize.DIALOG)
        else:
            self.__badge_artwork.get_style_context().remove_class(
                "artwork-icon")
            self.__badge_artwork.set_from_surface(surface)
        self.__badge_artwork.show()
