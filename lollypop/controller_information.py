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

from gi.repository import GLib

from lollypop.define import App, ArtBehaviour
from lollypop.objects_album import Album
from lollypop.objects_radio import Radio


class InformationController:
    """
        Information controller (title, artist, album, cover)
    """

    def __init__(self, show_tooltip=True, effect=ArtBehaviour.CACHE):
        """
            Init controller
            @param show_tooltip as bool
            @param effect as effect=ArtBehaviour
        """
        self._infobox = None
        self.__effect = effect
        self._previous_artwork_id = None
        self.__show_tooltip = show_tooltip
        self.__per_track_cover = App().settings.get_value(
            "allow-per-track-cover")

    def on_current_changed(self, art_size, font_size):
        """
            Update labels and cover and handles widget visibility
            @param art_size as int
            @param font_size as int
        """
        if App().player.current_track.id is None:
            if self._infobox is not None:
                self._infobox.hide()
            return
        elif self._infobox is not None:
            self._infobox.show()
        self.update_labels(font_size)
        self.update_artwork(art_size, art_size)

    def update_labels(self, font_size):
        """
            Update labels
            @param font_size as int
        """
        if isinstance(App().player.current_track, Radio):
            artist_text = App().player.current_track.name
        else:
            artist_text = ", ".join(App().player.current_track.artists)
        if font_size is None:
            self._artist_label.set_text(artist_text)
        else:
            self._artist_label.set_markup(
                "<span font='%s'>%s</span>" %
                (font_size - 2,
                 GLib.markup_escape_text(artist_text)))
        self._artist_label.show()

        title_text = App().player.current_track.title
        if font_size is None:
            self._title_label.set_text(title_text)
        else:
            self._title_label.set_markup(
                "<span font='%s'>%s</span>" %
                                        (font_size,
                                         GLib.markup_escape_text(title_text)))
        self._title_label.show()

    def update_artwork(self, width, height):
        """
            Update artwork
            @param width as int
            @param height as int
        """
        same_artwork = self._previous_artwork_id ==\
            App().player.current_track.album.id and not self.__per_track_cover
        if width < 1 or height < 1 or same_artwork:
            return
        self._previous_artwork_id = App().player.current_track.album.id
        scale_factor = self._artwork.get_scale_factor()
        if isinstance(App().player.current_track, Radio):
            App().art_helper.set_radio_artwork(
                App().player.current_track.name,
                width,
                height,
                scale_factor,
                self.__effect,
                self._on_artwork)
        elif App().player.current_track.id is not None:
            if self.__per_track_cover:
                effect = self.__effect | ArtBehaviour.NO_CACHE
                album = Album(App().player.current_track.album.id)
                App().art.clean_album_cache(album,
                                            width * scale_factor,
                                            height * scale_factor)
                album.set_tracks([App().player.current_track])
            else:
                effect = self.__effect
                album = App().player.current_track.album
            App().art_helper.set_album_artwork(
                album,
                width,
                height,
                scale_factor,
                effect,
                self._on_artwork)
            if self.__show_tooltip:
                self._artwork.set_tooltip_text(
                    App().player.current_track.album.name)

    def _on_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        self._artwork.set_from_surface(surface)

#######################
# PRIVATE             #
#######################
