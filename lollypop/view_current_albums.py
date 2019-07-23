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

from lollypop.view_albums_list import AlbumsListView
from lollypop.define import App, ViewType, MARGIN_SMALL
from lollypop.helper_size_allocation import SizeAllocationHelper


class CurrentAlbumsView(AlbumsListView, SizeAllocationHelper):
    """
        Popover showing Albums View
    """

    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        AlbumsListView.__init__(self, [], [], view_type)
        SizeAllocationHelper.__init__(self)
        if view_type & ViewType.DND:
            self.dnd_helper.connect("dnd-finished", self.__on_dnd_finished)
        self.__clear_button = Gtk.Button.new_from_icon_name(
            "edit-clear-all-symbolic",
            Gtk.IconSize.MENU)
        self.__clear_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__clear_button.set_tooltip_text(_("Clear albums"))
        self.__clear_button.get_style_context().add_class("light-button")
        self.__clear_button.get_style_context().add_class(
            "light-button-no-right-border")
        self.__clear_button.set_sensitive(App().player.albums)
        self.__clear_button.connect("clicked", self.__on_clear_clicked)
        self.__clear_button.set_margin_end(MARGIN_SMALL)
        self.__save_button = Gtk.Button.new_from_icon_name(
            "document-new-symbolic",
            Gtk.IconSize.MENU)
        self.__save_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__save_button.set_tooltip_text(_("Create a new playlist"))
        self.__save_button.get_style_context().add_class("light-button")
        self.__save_button.set_sensitive(App().player.albums)
        self.__save_button.connect("clicked", self.__on_save_clicked)
        self.__jump_button = Gtk.Button.new_from_icon_name(
            "go-jump-symbolic",
            Gtk.IconSize.MENU)
        self.__jump_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__jump_button.connect("clicked", self.__on_jump_clicked)
        self.__jump_button.get_style_context().add_class("light-button")
        self.__jump_button.set_tooltip_text(_("Go to current track"))
        self.__jump_button.set_sensitive(App().player.albums)
        label = Gtk.Label.new("<b>" + _("Playing albums") + "</b>")
        label.set_use_markup(True)
        label.set_hexpand(True)
        label.set_margin_start(2)
        label.get_style_context().add_class("dim-label")
        label.set_property("halign", Gtk.Align.START)
        self.__grid = Gtk.Grid()
        self.__grid.set_column_spacing(5)
        self.__grid.add(label)
        self.__grid.set_property("valign", Gtk.Align.CENTER)
        self.__grid.add(self.__jump_button)
        self.__grid.add(self.__save_button)
        self.__grid.add(self.__clear_button)
        self.__grid.show_all()
        self.set_row_spacing(2)
        self.insert_row(0)
        self.attach(self.__grid, 0, 0, 1, 1)
        self.__grid.set_property("halign", Gtk.Align.CENTER)
        self._box.set_property("halign", Gtk.Align.CENTER)

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        view_type = self._view_type & ~self.view_sizing_mask
        return ({"view_type": view_type}, self._sidebar_id, position)

#######################
# PRIVATE             #
#######################
    def __albums_to_playlist(self):
        """
            Create a new playlist based on search
        """
        tracks = []
        for child in self.children:
            tracks += child.album.tracks
        if tracks:
            import datetime
            now = datetime.datetime.now()
            date_string = now.strftime("%Y-%m-%d-%H:%M:%S")
            App().playlists.add(date_string)
            playlist_id = App().playlists.get_id(date_string)
            App().playlists.add_tracks(playlist_id, tracks)

    def _handle_size_allocate(self, allocation):
        """
            Change view width
            @param allocation as Gtk.Allocation
        """
        if SizeAllocationHelper._handle_size_allocate(self, allocation):
            width = allocation.width / 2
            self.__grid.set_size_request(width, -1)
            self._box.set_size_request(width, -1)

    def __on_jump_clicked(self, button):
        """
            Scroll to album
            @param button as Gtk.Button
        """
        self.jump_to_current()

    def __on_save_clicked(self, button):
        """
            Save to playlist
            @param button as Gtk.Button
        """
        button.set_sensitive(False)
        App().task_helper.run(self.__albums_to_playlist)

    def __on_clear_clicked(self, button):
        """
            Clear albums
            @param button as Gtk.Button
        """
        GLib.idle_add(self.clear, True)
        self.__clear_button.set_sensitive(False)
        self.__jump_button.set_sensitive(False)
        self.__save_button.set_sensitive(False)
        App().player.emit("status-changed")
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.popdown()

    def __on_dnd_finished(self, dnd_helper):
        """
            Save playlist if needed
            @param dnd_helper as DNDHelper
        """
        albums = []
        for child in self.children:
            albums.append(child.album)
        App().player.set_albums(albums)
