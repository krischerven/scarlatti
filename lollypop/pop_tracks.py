# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.view_tracks import TracksView
from lollypop.define import App, ViewType, ArtSize, ArtBehaviour
from lollypop.define import MARGIN_SMALL, Size
from lollypop.widgets_utils import Popover
from lollypop.helper_size_allocation import SizeAllocationHelper
from lollypop.controller_view import ViewController, ViewControllerType


class TracksPopover(Popover, ViewController, SizeAllocationHelper):
    """
        A popover with tracks
    """

    def __init__(self, album):
        """
            Init popover
            @param album as Album
            @param width as int
        """
        Popover.__init__(self)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        SizeAllocationHelper.__init__(self)
        self._album = album
        window_width = App().window.get_allocated_width()
        wanted_width = min(Size.NORMAL, window_width * 0.5)
        wanted_height = Size.MINI
        orientation = Gtk.Orientation.VERTICAL if wanted_width < Size.MEDIUM\
            else Gtk.Orientation.HORIZONTAL
        self.__tracks_view = TracksView(album, None, orientation,
                                        ViewType.TWO_COLUMNS | ViewType.ALBUM)
        self.__tracks_view.show()
        self.__tracks_view.connect("populated", self.__on_tracks_populated)
        self.__tracks_view.populate()
        self.__scrolled = Gtk.ScrolledWindow()
        self.__scrolled.add(self.__tracks_view)
        self.__scrolled.set_property("width-request", wanted_width)
        self.__scrolled.set_property("height-request", wanted_height)
        self.__scrolled.show()
        grid = Gtk.Grid()
        grid.set_column_spacing(MARGIN_SMALL)
        grid.show()
        overlay = Gtk.Overlay()
        overlay.set_property("width-request", ArtSize.SMALL)
        overlay.show()
        self.__artwork = Gtk.Image()
        self.__artwork.show()
        overlay.get_style_context().add_class("black")
        overlay.add(self.__artwork)
        # Play button
        play_button = Gtk.Button.new_from_icon_name(
           "media-playback-start-symbolic",
           Gtk.IconSize.DND)
        play_button.set_property("has-tooltip", True)
        play_button.set_tooltip_text(_("Play"))
        play_button.set_property("valign", Gtk.Align.START)
        play_button.set_property("halign", Gtk.Align.CENTER)
        play_button.set_margin_top(MARGIN_SMALL)
        play_button.connect("clicked", self.__on_play_clicked)
        play_button.show()
        play_button.get_style_context().add_class("vertical-menu-button")
        play_button.get_style_context().add_class("black-transparent")
        overlay.add_overlay(play_button)
        # Linked grid
        linked_grid = Gtk.Grid()
        linked_grid.set_orientation(Gtk.Orientation.VERTICAL)
        linked_grid.show()
        linked_grid.set_property("valign", Gtk.Align.END)
        linked_grid.set_property("halign", Gtk.Align.CENTER)
        linked_grid.get_style_context().add_class("linked")
        linked_grid.set_margin_bottom(MARGIN_SMALL)
        overlay.add_overlay(linked_grid)
        # Action button
        self.__action_button = Gtk.Button.new()
        self.__action_button.set_property("has-tooltip", True)
        self.__action_button.connect("clicked", self.__on_action_clicked)
        self.__action_button.set_image(Gtk.Image())
        self.__show_append(self._album.id not in App().player.album_ids)
        self.__action_button.show()
        linked_grid.add(self.__action_button)
        self.__action_button.get_style_context().add_class(
            "vertical-menu-button")
        self.__action_button.get_style_context().add_class("black-transparent")
        grid.add(overlay)
        grid.add(self.__scrolled)
        self.add(grid)

#######################
# PROTECTED           #
#######################
    def _handle_width_allocate(self, allocation):
        """
            Update artwork
            @param allocation as Gtk.Allocation
        """
        if SizeAllocationHelper._handle_width_allocate(self, allocation):
            App().art_helper.set_album_artwork(
                    self._album,
                    ArtSize.SMALL,
                    self.__scrolled.get_allocated_height(),
                    self.__artwork.get_scale_factor(),
                    ArtBehaviour.BLUR_MAX |
                    ArtBehaviour.CACHE |
                    ArtBehaviour.ROUNDED_BORDER |
                    ArtBehaviour.LIGHTER,
                    self.__on_album_artwork)

    def _on_current_changed(self, player):
        """
            Update view
            @param player as Player
        """
        self.__tracks_view.set_playing_indicator()
        self.__show_append(self._album.id not in App().player.album_ids)

    def _on_duration_changed(self, player, track_id):
        """
            Update track duration
            @param player as Player
            @param track_id as int
        """
        self.__tracks_view.update_duration(track_id)

#######################
# PRIVATE             #
#######################
    def __show_append(self, append):
        """
           Show append button if append, else remove button
        """
        if append:
            self.__action_button.get_image().set_from_icon_name(
                                                 "list-add-symbolic",
                                                 Gtk.IconSize.DND)
            self.__action_button.set_tooltip_text(_("Add to current playlist"))
        else:
            self.__action_button.get_image().set_from_icon_name(
                                                   "list-remove-symbolic",
                                                   Gtk.IconSize.DND)
            self.__action_button.set_tooltip_text(
                _("Remove from current playlist"))

    def __on_play_clicked(self, button):
        """
            Play album
           @param button as Gtk.Button
        """
        App().player.play_album(self._album)
        self.__show_append(False)

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
            self.__show_append(True)
        else:
            if App().player.is_playing and not App().player.albums:
                App().player.play_album(self._album)
            else:
                App().player.add_album(self._album)
            self.__show_append(False)
        App().player.update_next_prev()

    def __on_play_all_clicked(self, button):
        """
            Play album with context
            @param button as Gtk.Button
        """
        self.__show_append(False)
        if App().player.is_party:
            App().lookup_action("party").change_state(GLib.Variant("b", False))
        self.emit("play-all-from")

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if surface is not None:
            self.__artwork.set_from_surface(surface)

    def __on_tracks_populated(self, view):
        """
            Tracks populated
            @param view as TracksView
        """
        if not self.__tracks_view.is_populated:
            self.__tracks_view.populate()
