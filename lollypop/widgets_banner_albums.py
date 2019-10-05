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

from gi.repository import Gtk, GLib, GObject

from lollypop.define import App, ArtSize, ViewType, Type, MARGIN
from lollypop.widgets_banner import BannerWidget
from lollypop.shown import ShownLists
from lollypop.utils import update_button, emit_signal


class AlbumsBannerWidget(BannerWidget):
    """
        Banner for albums
    """

    __gsignals__ = {
        "play-all": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init banner
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
        """
        BannerWidget.__init__(self, view_type)
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        grid = Gtk.Grid.new()
        grid.show()
        grid.set_property("valign", Gtk.Align.CENTER)
        self.__title_label = Gtk.Label.new()
        self.__title_label.show()
        self.__title_label.set_margin_start(MARGIN)
        self.__title_label.set_hexpand(True)
        self.__title_label.set_property("halign", Gtk.Align.START)
        linked = Gtk.Grid.new()
        linked.show()
        linked.get_style_context().add_class("linked")
        linked.set_margin_end(MARGIN)
        linked.set_property("halign", Gtk.Align.END)
        self.__play_button = Gtk.Button.new()
        self.__play_button.show()
        self.__play_button.get_style_context().add_class(
            "black-transparent")
        self.__play_button.connect("clicked", self.__on_play_button_clicked)
        image = Gtk.Image.new()
        image.show()
        self.__play_button.set_image(image)
        self.__shuffle_button = Gtk.Button.new()
        self.__shuffle_button.show()
        self.__shuffle_button.get_style_context().add_class(
            "black-transparent")
        image = Gtk.Image.new()
        image.show()
        self.__shuffle_button.set_image(image)
        self.__shuffle_button.connect("clicked",
                                      self.__on_shuffle_button_clicked)
        linked.add(self.__play_button)
        linked.add(self.__shuffle_button)
        grid.add(self.__title_label)
        grid.add(linked)
        self._overlay.add_overlay(grid)
        self._overlay.set_overlay_pass_through(grid, True)
        if genre_ids and genre_ids[0] == Type.YEARS and artist_ids:
            title_str = "%s - %s" % (artist_ids[0], artist_ids[-1])
        else:
            genres = []
            for genre_id in genre_ids:
                if genre_id < 0:
                    genres.append(ShownLists.IDS[genre_id])
                else:
                    genres.append(App().genres.get_name(genre_id))
            title_str = ",".join(genres)
        self.__title_label.set_markup("<b>%s</b>" %
                                      GLib.markup_escape_text(title_str))

    def set_view_type(self, view_type):
        """
            Update view type
            @param view_type as ViewType
        """
        BannerWidget.set_view_type(self, view_type)
        title_context = self.__title_label.get_style_context()
        for c in title_context.list_classes():
            title_context.remove_class(c)
        if view_type & ViewType.ADAPTIVE:
            style = "menu-button"
            icon_size = Gtk.IconSize.BUTTON
            title_context.add_class("text-large")
        else:
            style = "menu-button-48"
            icon_size = Gtk.IconSize.LARGE_TOOLBAR
            title_context.add_class("text-x-large")
        update_button(self.__play_button, style,
                      icon_size, "media-playback-start-symbolic")
        update_button(self.__shuffle_button, style,
                      icon_size, "media-playlist-shuffle-symbolic")

    @property
    def height(self):
        """
            Get wanted height
            @return int
        """
        return ArtSize.SMALL

#######################
# PRIVATE             #
#######################
    def __on_play_button_clicked(self, button):
        """
            Play playlist
            @param button as Gtk.Button
        """
        emit_signal(self, "play-all", False)

    def __on_shuffle_button_clicked(self, button):
        """
            Play playlist shuffled
            @param button as Gtk.Button
        """
        emit_signal(self, "play-all", True)
