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

from lollypop.define import App, ArtSize, MARGIN, Type, ViewType
from lollypop.define import ArtBehaviour
from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.widgets_cover import CoverWidget
from lollypop.utils import get_human_duration, on_query_tooltip, on_realize


class AlbumBannerWidget(Gtk.Bin):
    """
        Banner for album
    """

    def __init__(self, album, view_type=ViewType.DEFAULT):
        """
            Init cover widget
            @param album
            @param view_type as ViewType
        """
        Gtk.Bin.__init__(self)
        self.__view_type = view_type
        self.__height = None
        self.__width = 0
        self.__cloud_image = None
        self.__allocation_timeout_id = None
        self.__album = album
        self.set_property("valign", Gtk.Align.START)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AlbumBannerWidget.ui")
        builder.connect_signals(self)
        self.__title_label = builder.get_object("name_label")
        self.__title_label.connect("query-tooltip", on_query_tooltip)
        self.__year_label = builder.get_object("year_label")
        self.__duration_label = builder.get_object("duration_label")
        self.__menu_button = builder.get_object("menu_button")
        self.__cover_widget = CoverWidget(album, view_type)
        self.__cover_widget.set_vexpand(True)
        self.__cover_widget.show()
        album_name = GLib.markup_escape_text(album.name)
        markup = "<b>%s</b>" % album_name
        if view_type & ViewType.ALBUM:
            artist_name = GLib.markup_escape_text(", ".join(album.artists))
            if view_type & ViewType.SMALL:
                markup += "\n<span alpha='40000'>%s</span>" % artist_name
            else:
                markup += "\n<span size='x-small' alpha='40000'>%s</span>" %\
                                                                  artist_name
        self.__title_label.set_markup(markup)
        if album.year is not None:
            self.__year_label.set_text(str(album.year))
        else:
            self.__year_label.hide()
        year_eventbox = builder.get_object("year_eventbox")
        year_eventbox.connect("realize", on_realize)
        year_eventbox.connect("button-release-event",
                              self.__on_year_button_release_event)
        duration = App().albums.get_duration(self.__album.id,
                                             self.__album.genre_ids)
        self.__duration_label.set_text(get_human_duration(duration))
        self.__artwork = builder.get_object("artwork")
        self.__grid = builder.get_object("grid")
        self.__widget = builder.get_object("widget")
        if view_type & ViewType.ALBUM:
            self.__menu_button.get_style_context().add_class(
                "black-transparent")
            self.get_style_context().add_class("black")
            self.__artwork.get_style_context().add_class("black")
            self.connect("size-allocate", self.__on_size_allocate)
            self.connect("destroy", self.__on_destroy)
            self.__art_signal_id = App().art.connect(
                                               "album-artwork-changed",
                                               self.__on_album_artwork_changed)
        else:
            self.__grid.get_style_context().add_class("banner-frame")
        self.__grid.attach(self.__cover_widget, 0, 0, 1, 3)
        self.__rating_grid = builder.get_object("rating_grid")
        if album.mtime <= 0:
            self.__cloud_image = Gtk.Image.new()
            self.__cloud_image.show()
            self.__cloud_image.set_margin_start(MARGIN)
            self.__rating_grid.attach(self.__cloud_image, 1, 0, 1, 1)
        self.__rating_widget = RatingWidget(album, Gtk.IconSize.INVALID)
        self.__rating_widget.set_property("halign", Gtk.Align.START)
        self.__rating_widget.set_property("valign", Gtk.Align.CENTER)
        self.__rating_widget.show()
        self.__rating_grid.attach(self.__rating_widget, 2, 0, 1, 1)
        self.__loved_widget = LovedWidget(album, Gtk.IconSize.INVALID)
        self.__loved_widget.set_margin_start(10)
        self.__loved_widget.set_property("halign", Gtk.Align.START)
        self.__loved_widget.set_property("valign", Gtk.Align.CENTER)
        self.__loved_widget.show()
        self.__rating_grid.attach(self.__loved_widget, 3, 0, 1, 1)
        self.add(self.__widget)
        self.__cover_widget.set_margin_start(MARGIN)
        self.__year_label.set_margin_end(MARGIN)
        self.__duration_label.set_margin_start(MARGIN)
        self.__rating_grid.set_margin_end(MARGIN)
        self.set_view_type(view_type)

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        self.__view_type = view_type
        art_size = 0
        if view_type & ViewType.SMALL:
            art_size = ArtSize.LARGE
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
            self.__title_label.get_style_context().add_class(
                "text-large")
            self.__year_label.get_style_context().add_class(
                "text-large")
        elif view_type & ViewType.MEDIUM:
            art_size = ArtSize.BANNER
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            self.__title_label.get_style_context().add_class(
                "text-x-large")
            self.__year_label.get_style_context().add_class(
                "text-large")
        else:
            art_size = ArtSize.BANNER
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            self.__title_label.get_style_context().add_class(
                "text-xx-large")
            self.__year_label.get_style_context().add_class(
                "text-x-large")
        self.__rating_widget.set_icon_size(icon_size)
        self.__loved_widget.set_icon_size(icon_size)
        if self.__cloud_image is not None:
            self.__cloud_image.set_from_icon_name("goa-panel-symbolic",
                                                  icon_size)
        self.__cover_widget.set_artwork(art_size)
        menu_button_style_context = self.__menu_button.get_style_context()
        menu_button_style_context.remove_class("menu-button-48")
        menu_button_style_context.remove_class("menu-button")
        menu_button_style_context.add_class(style)
        self.__menu_button.get_image().set_from_icon_name(
                                                   "view-more-symbolic",
                                                   icon_size)
        self.set_height(self.height)

    def set_height(self, height):
        """
            Set height
            @param height as int
        """
        if height < self.default_height:
            self.__height = height
            # Make grid cover artwork
            # No idea why...
            self.__grid.set_size_request(-1, height + 1)
            self.__cover_widget.hide()
            self.__duration_label.hide()
            self.__rating_grid.hide()
            self.__year_label.set_vexpand(True)
            self.__set_text_height(True)
        else:
            self.__height = None
            # Make grid cover artwork
            # No idea why...
            self.__grid.set_size_request(-1, height + 1)
            self.__cover_widget.show()
            self.__duration_label.show()
            self.__rating_grid.show()
            self.__year_label.set_vexpand(False)
            self.__set_text_height(False)

    def do_get_preferred_width(self):
        """
            Force preferred width
        """
        return (0, 0)

    def do_get_preferred_height(self):
        """
            Force preferred height
        """
        return (self.height, self.height)

    def set_selected(self, selected):
        """
            Mark widget as selected
            @param selected as bool
        """
        if selected:
            self.__grid.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self.__grid.set_state_flags(Gtk.StateFlags.NORMAL, True)

    @property
    def height(self):
        """
            Get height
            @return int
        """
        return self.__height if self.__height is not None\
            else self.default_height

    @property
    def default_height(self):
        """
            Get default height
        """
        if self.__view_type & ViewType.SMALL:
            return ArtSize.LARGE + 40
        elif self.__view_type & ViewType.MEDIUM:
            return ArtSize.BANNER + 40
        else:
            return ArtSize.BANNER + 40

#######################
# PROTECTED           #
#######################
    def _on_menu_button_clicked(self, button):
        """
            Show album menu
            @param button as Gtk.Button
        """
        from lollypop.menu_objects import AlbumMenu
        menu = AlbumMenu(self.__album, self.__view_type)
        popover = Gtk.Popover.new_from_model(button, menu)
        popover.popup()

#######################
# PRIVATE             #
#######################
    def __set_text_height(self, collapsed):
        """
            Set text height
            @param collapsed as bool
        """
        title_context = self.__title_label.get_style_context()
        year_context = self.__year_label.get_style_context()
        for c in title_context.list_classes():
            title_context.remove_class(c)
        for c in year_context.list_classes():
            title_context.remove_class(c)
        if self.__view_type & ViewType.SMALL:
            if not collapsed:
                self.__title_label.get_style_context().add_class("text-large")
        # Collapsed not implemented for MEDIUM
        elif self.__view_type & ViewType.MEDIUM:
            self.__title_label.get_style_context().add_class(
                "text-x-large")
            self.__year_label.get_style_context().add_class(
                "text-large")
        elif collapsed:
            self.__title_label.get_style_context().add_class(
                "text-x-large")
            self.__year_label.get_style_context().add_class(
                "text-large")
        else:
            self.__title_label.get_style_context().add_class(
                "text-xx-large")
            self.__year_label.get_style_context().add_class(
                "text-x-large")

    def __handle_size_allocate(self, allocation):
        """
            Change box max/min children
            @param allocation as Gtk.Allocation
        """
        self.__allocation_timeout_id = None
        if allocation.width == 1 or self.__width == allocation.width:
            return
        self.__width = allocation.width
        App().art_helper.set_album_artwork(
                self.__album,
                # +100 to prevent resize lag
                allocation.width + 100,
                self.default_height,
                self.__artwork.get_scale_factor(),
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

    def __on_album_artwork_changed(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album_id as int
        """
        if album_id == self.__album.id:
            App().art_helper.set_album_artwork(
                            self.__album,
                            # +100 to prevent resize lag
                            self.get_allocated_width() + 100,
                            self.default_height,
                            self.__artwork.get_scale_factor(),
                            ArtBehaviour.BLUR_HARD |
                            ArtBehaviour.DARKER,
                            self.__on_album_artwork)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is not None:
            self.__artwork.set_from_surface(surface)

    def __on_year_button_release_event(self, widget, event):
        """
            Show year view
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        App().window.emit("can-go-back-changed", True)
        App().window.emit("show-can-go-back", True)
        App().window.container.show_view([Type.YEARS], [self.__album.year])

    def __on_size_allocate(self, widget, allocation):
        """
            Delayed handling
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__allocation_timeout_id is not None:
            GLib.source_remove(self.__allocation_timeout_id)
        self.__allocation_timeout_id = GLib.idle_add(
            self.__handle_size_allocate, allocation)
