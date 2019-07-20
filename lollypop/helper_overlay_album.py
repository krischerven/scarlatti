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

from lollypop.define import App, ViewType
from lollypop.utils import on_realize
from lollypop.helper_overlay import OverlayHelper


class OverlayAlbumHelper(OverlayHelper):
    """
        An overlay helper for albums
    """

    def __init__(self, view_type=ViewType.DEFAULT):
        """
            Init helper
            @param view_type as ViewType
        """
        OverlayHelper.__init__(self)
        OverlayAlbumHelper.set_view_type(self, view_type)

    def set_view_type(self, view_type):
        """
            Update pixel size
            @param view_type as ViewType
        """
        if view_type & ViewType.SMALL:
            self.__play_pixel_size = -1
        elif view_type & ViewType.MEDIUM:
            self.__play_pixel_size = self._pixel_size
        else:
            self.__play_pixel_size = self._pixel_size + 20
        self.show_overlay(False)

    def show_overlay(self, show):
        """
            Set overlay
            @param show as bool
        """
        if (show and self._big_grid is not None) or\
                (not show and self._big_grid is None):
            return
        OverlayHelper.show_overlay(self, show)
        if show:
            if self.__play_pixel_size > 0:
                # Play button
                self.__play_button = Gtk.Button.new_from_icon_name(
                    "media-playback-start-symbolic",
                    Gtk.IconSize.INVALID)
                self.__play_button.get_image().set_pixel_size(
                    self.__play_pixel_size)
                self.__play_button.set_property("has-tooltip", True)
                self.__play_button.set_tooltip_text(_("Play"))
                self.__play_button.connect("realize", on_realize)
                self.__play_button.connect("clicked", self.__on_play_clicked)
                self.__play_button.show()
                self._big_grid.add(self.__play_button)
                self.__play_button.get_style_context().add_class(
                    "overlay-button-rounded")
            # Action button
            self.__action_button = Gtk.Button.new()
            self.__action_button.set_property("has-tooltip", True)
            self.__action_button.connect("realize", on_realize)
            self.__action_button.connect("clicked", self.__on_action_clicked)
            self.__action_button.set_image(Gtk.Image())
            self.__action_button.get_image().set_pixel_size(self._pixel_size)
            self._show_append(self._album.id not in App().player.album_ids)
            self.__action_button.show()
            self._small_grid.add(self.__action_button)
            self.__action_button.get_style_context().add_class(
                    "overlay-button")
        else:
            if self.__play_pixel_size > 0:
                self.__play_button.destroy()
                self.__play_button = None
            self.__action_button.destroy()
            self.__action_button = None

#######################
# PROTECTED           #
#######################
    def _show_append(self, append):
        """
            Show append button if append, else remove button
        """
        if append:
            self.__action_button.get_image().set_from_icon_name(
                                                  "list-add-symbolic",
                                                  Gtk.IconSize.INVALID)
            self.__action_button.set_tooltip_text(_("Add to current playlist"))
        else:
            self.__action_button.get_image().set_from_icon_name(
                                                   "list-remove-symbolic",
                                                   Gtk.IconSize.INVALID)
            self.__action_button.set_tooltip_text(
                _("Remove from current playlist"))

#######################
# PRIVATE             #
#######################
    def __on_play_clicked(self, button):
        """
            Play album
            @param button as Gtk.Button
        """
        if App().player.is_party:
            action = App().lookup_action("party")
            action.change_state(GLib.Variant("b", False))
        App().player.play_album(self._album.clone(True))
        self._show_append(False)
        return True

    def __on_action_clicked(self, button):
        """
            Append album to current list if not present
            Remove it if present
            @param button as Gtk.Button
        """
        if self._album.id in App().player.album_ids:
            if App().player.current_track.album.id == self._album.id:
                # If not last album, skip it
                if len(App().player.albums) > 1:
                    App().player.skip_album()
                    App().player.remove_album_by_id(self._album.id)
                # remove it and stop playback by going to next track
                else:
                    App().player.remove_album_by_id(self._album.id)
                    App().player.stop()
            else:
                App().player.remove_album_by_id(self._album.id)
            self._show_append(True)
        else:
            if App().player.is_playing and not App().player.albums:
                App().player.play_album(self._album.clone(True))
            else:
                App().player.add_album(self._album.clone(True))
            self._show_append(False)
        return True
