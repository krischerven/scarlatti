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

from gi.repository import Gtk, Pango

from gettext import gettext as _

from lollypop.define import App, ArtSize, ViewType
from lollypop.define import MARGIN, MARGIN_SMALL
from lollypop.widgets_banner import BannerWidget
from lollypop.utils import update_button


class CurrentAlbumsBannerWidget(BannerWidget):
    """
        Banner for current albums
    """

    def __init__(self, view):
        """
            Init banner
            @param view as AlbumsListView
        """
        BannerWidget.__init__(self, view.args[0]["view_type"])
        self.__view = view
        self.__clear_button = Gtk.Button.new_from_icon_name(
            "edit-clear-all-symbolic",
            Gtk.IconSize.LARGE_TOOLBAR)
        self.__clear_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__clear_button.set_tooltip_text(_("Clear albums"))
        self.__clear_button.set_sensitive(App().player.albums)
        self.__clear_button.connect("clicked", self.__on_clear_clicked)
        self.__clear_button.get_style_context().add_class("black-transparent")
        self.__clear_button.show()
        self.__save_button = Gtk.Button.new_from_icon_name(
            "document-new-symbolic",
            Gtk.IconSize.LARGE_TOOLBAR)
        self.__save_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__save_button.set_tooltip_text(_("Create a new playlist"))
        self.__save_button.set_sensitive(App().player.albums)
        self.__save_button.connect("clicked", self.__on_save_clicked)
        self.__save_button.get_style_context().add_class("black-transparent")
        self.__save_button.show()
        self.__jump_button = Gtk.Button.new_from_icon_name(
            "go-jump-symbolic",
            Gtk.IconSize.LARGE_TOOLBAR)
        self.__jump_button.set_relief(Gtk.ReliefStyle.NONE)
        self.__jump_button.connect("clicked", self.__on_jump_clicked)
        self.__jump_button.set_tooltip_text(_("Go to current track"))
        self.__jump_button.set_sensitive(App().player.albums)
        self.__jump_button.get_style_context().add_class("black-transparent")
        self.__jump_button.show()
        self.__title_label = Gtk.Label.new(
            "<b>" + _("Playing albums") + "</b>")
        self.__title_label.show()
        self.__title_label.set_use_markup(True)
        self.__title_label.set_hexpand(True)
        self.__title_label.get_style_context().add_class("dim-label")
        self.__title_label.set_property("halign", Gtk.Align.START)
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        grid = Gtk.Grid()
        grid.show()
        grid.set_column_spacing(MARGIN_SMALL)
        grid.set_property("valign", Gtk.Align.CENTER)
        grid.set_margin_start(MARGIN)
        grid.set_margin_end(MARGIN)
        grid.add(self.__title_label)
        buttons = Gtk.Grid()
        buttons.show()
        buttons.get_style_context().add_class("linked")
        buttons.set_property("valign", Gtk.Align.CENTER)
        buttons.add(self.__jump_button)
        buttons.add(self.__save_button)
        buttons.add(self.__clear_button)
        grid.add(buttons)
        self._overlay.add_overlay(grid)
        self._overlay.set_overlay_pass_through(grid, True)

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
        update_button(self.__clear_button, style,
                      icon_size, "edit-clear-all-symbolic")
        update_button(self.__save_button, style,
                      icon_size, "document-new-symbolic")
        update_button(self.__jump_button, style,
                      icon_size, "go-jump-symbolic")

    @property
    def spinner(self):
        """
            Get banner spinner
            @return Gtk.Spinner
        """
        return self.__spinner

    @property
    def entry(self):
        """
            Get banner entry
            @return Gtk.Entry
        """
        return self.__entry

    @property
    def clear_button(self):
        """
            Get clear button
            @return Gtk.Button
        """
        return self.__clear_button

    @property
    def save_button(self):
        """
            Get save button
            @return Gtk.Button
        """
        return self.__save_button

    @property
    def jump_button(self):
        """
            Get jump button
            @return Gtk.Button
        """
        return self.__jump_button

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
            playlist_id = App().playlists.add(date_string)
            App().playlists.add_tracks(playlist_id, tracks)

    def __on_jump_clicked(self, button):
        """
            Scroll to album
            @param button as Gtk.Button
        """
        self.__view.jump_to_current()

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
        self.__view.clear(True)
        self.__view.populate([])
        self.__clear_button.set_sensitive(False)
        self.__jump_button.set_sensitive(False)
        self.__save_button.set_sensitive(False)
        App().player.emit("status-changed")
