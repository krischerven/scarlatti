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

from lollypop.define import App, ArtSize, ViewType, Type
from lollypop.widgets_banner import BannerWidget
from lollypop.shown import ShownLists
from lollypop.utils import update_button


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
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/Lollypop/AlbumsBannerWidget.ui")
        self.__title_label = builder.get_object("title")
        self.__duration_label = builder.get_object("duration")
        self.__play_button = builder.get_object("play_button")
        self.__shuffle_button = builder.get_object("shuffle_button")
        widget = builder.get_object("widget")
        self._overlay.add_overlay(widget)
        self._overlay.set_overlay_pass_through(widget, True)
        if genre_ids and genre_ids[0] == Type.YEARS:
            decade_str = "%s - %s" % (artist_ids[0], artist_ids[-1])
            self.__title_label.set_label(decade_str)
        else:
            genres = []
            for genre_id in genre_ids:
                if genre_id < 0:
                    genres.append(ShownLists.IDS[genre_id])
                else:
                    genres.append(App().genres.get_name(genre_id))
            self.__title_label.set_label(",".join(genres))
        builder.connect_signals(self)

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
        if view_type & ViewType.MEDIUM:
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
        self.emit("play-all", False)

    def _on_shuffle_button_clicked(self, button):
        """
            Play playlist shuffled
            @param button as Gtk.Button
        """
        self.emit("play-all", True)
