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

from lollypop.define import App, Shuffle
from lollypop.objects_track import Track
from lollypop.objects_album import Album, Disc
from lollypop.utils import on_realize, tracks_to_albums
from lollypop.helper_overlay import OverlayHelper


class OverlayPlaylistHelper(OverlayHelper):
    """
        An overlay helper for a playlist
    """

    def __init__(self):
        """
            Init helper
        """
        OverlayHelper.__init__(self)

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
            # Play button
            if self._obj is None:
                self.__play_button = Gtk.Button.new_from_icon_name(
                    "media-playback-start-symbolic",
                    Gtk.IconSize.INVALID)
                self.__play_button.set_tooltip_text(_("Play"))
                self._big_grid.set_margin_bottom(10)
                self._big_grid.set_margin_start(10)
            else:
                self._big_grid.set_property("valign", Gtk.Align.CENTER)
                self._big_grid.set_property("halign", Gtk.Align.CENTER)
                if self._add:
                    # Special case, we are in add to playlist mode
                    self.__play_button = Gtk.Button.new_from_icon_name(
                        "list-add-symbolic",
                        Gtk.IconSize.INVALID)
                    self.__play_button.set_tooltip_text(_("Add"))
                else:
                    # Special case, we are in remove from playlist mode
                    self.__play_button = Gtk.Button.new_from_icon_name(
                        "list-remove-symbolic",
                        Gtk.IconSize.INVALID)
                    self.__play_button.set_tooltip_text(_("Remove"))
            self.__play_button.set_property("has-tooltip", True)
            self.__play_button.connect("realize", on_realize)
            self.__play_button.connect("button-release-event",
                                       self.__on_play_button_release_event)
            self.__play_button.get_image().set_pixel_size(self._pixel_size +
                                                          20)
            self.__play_button.show()
            # Edit button
            self.__edit_button = Gtk.Button.new_from_icon_name(
                "document-properties-symbolic",
                Gtk.IconSize.INVALID)
            self.__edit_button.set_property("has-tooltip", True)
            self.__edit_button.set_tooltip_text(_("Modify playlist"))
            self.__edit_button.connect("realize", on_realize)
            self.__edit_button.connect("button-release-event",
                                       self.__on_edit_button_release_event)
            self.__edit_button.get_image().set_pixel_size(self._pixel_size)
            self.__edit_button.show()
            self._big_grid.add(self.__play_button)
            self._small_grid.set_margin_bottom(10)
            self._small_grid.set_margin_end(25)
            self._small_grid.add(self.__edit_button)
            self.__play_button.get_style_context().add_class(
                "overlay-button-rounded")
            self.__edit_button.get_style_context().add_class("overlay-button")
            self._small_grid.get_style_context().add_class(
                "squared-icon-small")
        else:
            self.__play_button.destroy()
            self.__play_button = None
            self.__edit_button.destroy()
            self.__edit_button = None

#######################
# PRIVATE             #
#######################
    def __on_play_button_release_event(self, button, event):
        """
            Play playlist
            @param button as Gtk.Button
            @param event as Gdk.EventButton
        """
        if self._obj is None:
            if self._track_ids:
                if App().player.is_party:
                    App().lookup_action("party").change_state(
                        GLib.Variant("b", False))
                tracks = [Track(track_id) for track_id in self._track_ids]
                if App().settings.get_enum("shuffle") == Shuffle.TRACKS:
                    track = choice(tracks)
                else:
                    track = tracks[0]
                albums = tracks_to_albums(tracks)
                App().player.play_track_for_albums(track, albums)
        else:
            if isinstance(self._obj, Disc):
                tracks = self._obj.tracks
            elif isinstance(self._obj, Album):
                tracks = self._obj.tracks
            else:
                tracks = [self._obj]
            if self._add:
                App().playlists.add_tracks(self._data, tracks)
            else:
                App().playlists.remove_tracks(self._data, tracks)
            App().window.go_back()
        return True

    def __on_edit_button_release_event(self, button, event):
        """
            Edit playlist
            @param button as Gtk.Button
            @param event as Gdk.EventButton
        """
        from lollypop.pop_playlist_edit import PlaylistEditPopover
        popover = PlaylistEditPopover(self._data)
        popover.set_relative_to(button)
        popover.connect("closed", self._on_popover_closed)
        self._lock_overlay = True
        popover.popup()
        return True
