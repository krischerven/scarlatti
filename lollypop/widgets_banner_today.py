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

from gi.repository import Gtk, GLib, Pango

from pickle import load, dump
from gettext import gettext as _

from lollypop.define import App, ArtSize, MARGIN, ViewType
from lollypop.define import ArtBehaviour, LOLLYPOP_DATA_PATH
from lollypop.widgets_banner import BannerWidget
from lollypop.widgets_cover import CoverWidget
from lollypop.objects_album import Album
from lollypop.utils import update_button
from lollypop.logger import Logger


class TodayBannerWidget(BannerWidget):
    """
        Banner for today album
    """

    def get_today_album():
        """
            Get today album
            @return Album
        """
        current_date = GLib.DateTime.new_now_local().get_day_of_year()
        (date, album_id) = (0, None)
        try:
            (date, album_id) = load(
                open(LOLLYPOP_DATA_PATH + "/today.bin", "rb"))
        except Exception as e:
            Logger.warning("TodayBannerWidget::__get_today_album(): %s", e)
        try:
            if date != current_date:
                album_id = App().albums.get_randoms(1)[0]
                dump((current_date, album_id),
                     open(LOLLYPOP_DATA_PATH + "/today.bin", "wb"))
            return Album(album_id)
        except Exception as e:
            Logger.error("TodayBannerWidget::__get_today_album(): %s", e)
        return Album()

    def __init__(self, album, view_type=ViewType.DEFAULT):
        """
            Init cover widget
            @param album
            @param view_type as ViewType
        """
        BannerWidget.__init__(self, view_type)
        self.__album = album
        album_name = GLib.markup_escape_text(self.__album.name)
        self.__title_label = Gtk.Label.new()
        self.__title_label.show()
        markup = _("<b>Album of the day: </b>\n")
        markup += "<span size='small' alpha='40000'>%s</span>\n" % album_name
        artist_name = GLib.markup_escape_text(", ".join(self.__album.artists))
        markup += "<span size='x-small' alpha='40000'>%s</span>" % artist_name
        self.__title_label.set_markup(markup)
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__cover_widget = CoverWidget(self.__album,
                                          view_type | ViewType.MEDIUM)
        self.__cover_widget.show()
        self.__cover_widget.set_vexpand(True)
        self.__play_button = Gtk.Button.new()
        self.__play_button.show()
        image = Gtk.Image.new()
        image.show()
        self.__play_button.set_image(image)
        self.__play_button.connect("clicked", self.__on_play_button_clicked)
        self.__play_button.get_style_context().add_class("black-transparent")
        self.__play_button.set_property("valign", Gtk.Align.CENTER)
        self.__play_button.set_property("halign", Gtk.Align.END)
        self.__play_button.set_hexpand(True)
        update_button(self.__play_button, "menu-button-48",
                      Gtk.IconSize.LARGE_TOOLBAR,
                      "media-playback-start-symbolic")
        grid = Gtk.Grid()
        grid.show()
        grid.set_column_spacing(MARGIN)
        grid.add(self.__cover_widget)
        grid.add(self.__title_label)
        grid.add(self.__play_button)
        grid.set_margin_start(MARGIN)
        grid.set_margin_end(MARGIN)
        self._overlay.add_overlay(grid)
        self._overlay.set_overlay_pass_through(grid, True)
        self.set_reveal_child(False)
        self.connect("map", self.__on_map)

    def set_view_type(self, view_type):
        """
            Update widget internals for view_type
            @param view_type as ViewType
        """
        BannerWidget.set_view_type(self, view_type)
        if view_type & ViewType.MEDIUM:
            art_size = ArtSize.MEDIUM
        else:
            art_size = ArtSize.BANNER
        self.__cover_widget.set_artwork(art_size)
        self.__set_text_height()

#######################
# PROTECTED           #
#######################
    def _handle_size_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if BannerWidget._handle_size_allocate(self, allocation):
            App().art_helper.set_album_artwork(
                    self.__album,
                    # +100 to prevent resize lag
                    allocation.width + 100,
                    ArtSize.BANNER + MARGIN * 2,
                    self._artwork.get_scale_factor(),
                    ArtBehaviour.BLUR_HARD |
                    ArtBehaviour.DARKER,
                    self.__on_album_artwork)

    def _on_play_button_clicked(self, button):
        """
            Play album
           @param button as Gtk.Button
        """
        App().player.play_album(self.__album)

#######################
# PRIVATE             #
#######################
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

    def __on_map(self, widget):
        """
            Show banner
            @param widget as Gtk.Widget
        """
        def show():
            self.set_transition_duration(500)
            self.set_reveal_child(True)
            self.set_transition_duration(250)

        GLib.timeout_add(250, show)

    def __on_play_button_clicked(self, button):
        """
            Play album
            @param button as Gtk.Button
        """
        App().player.play_album(self.__album)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is not None:
            self._artwork.set_from_surface(surface)
        else:
            App().art_helper.set_banner_artwork(
                # +100 to prevent resize lag
                self.get_allocated_width() + 100,
                ArtSize.BANNER + MARGIN * 2,
                self._artwork.get_scale_factor(),
                ArtBehaviour.BLUR |
                ArtBehaviour.DARKER,
                self.__on_album_artwork)