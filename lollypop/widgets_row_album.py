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

from gi.repository import Gtk, Gio, GLib, GObject, Pango

from gettext import gettext as _

from lollypop.view_tracks import TracksView
from lollypop.define import ArtSize, App, ViewType, MARGIN_SMALL, Type
from lollypop.define import ArtBehaviour, StorageType
from lollypop.helper_gestures import GesturesHelper


class AlbumRow(Gtk.ListBoxRow, TracksView):
    """
        Album row
    """

    __gsignals__ = {
        "remove-from-playlist": (GObject.SignalFlags.RUN_FIRST, None,
                                 (GObject.TYPE_PYOBJECT,)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    __MARGIN = 4

    def get_best_height(widget):
        """
            Helper to pass object it's height request
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(AlbumRow.__MARGIN * 2 +
                          2 * layout.get_pixel_size()[1])
        cover_height = AlbumRow.__MARGIN * 2 + ArtSize.SMALL
        if font_height > cover_height:
            return font_height + 2
        else:
            return cover_height + 2

    def __init__(self, album, height, view_type, reveal, position):
        """
            Init row widgets
            @param album as Album
            @param height as int
            @param view_type as ViewType
            @param reveal as bool
            @param parent as AlbumListView
            @param position as int
        """
        Gtk.ListBoxRow.__init__(self)
        self._view_type = view_type
        TracksView.__init__(self, None, Gtk.Orientation.VERTICAL, position)
        self.__revealer = None
        self.__reveal = reveal
        self._artwork = None
        self._album = album
        self.__cancellable = Gio.Cancellable()
        self.set_sensitive(False)
        self.set_property("height-request", height)
        self.connect("destroy", self.__on_destroy)

    def populate(self):
        """
            Populate widget content
        """
        if self.get_child() is not None:
            return
        self._artwork = Gtk.Image.new()
        App().art_helper.set_frame(self._artwork, "small-cover-frame",
                                   ArtSize.SMALL, ArtSize.SMALL)
        self._artwork.set_margin_start(self.__MARGIN)
        # Little hack: we do not set margin_bottom because already set by
        # get_best_height(): we are Align.FILL
        # This allow us to not Align.CENTER row_widget and not jump up
        # and down on reveal()
        self._artwork.set_margin_top(self.__MARGIN)
        self.get_style_context().add_class("albumrow")
        self.set_sensitive(True)
        self.set_property("has-tooltip", True)
        self.connect("query-tooltip", self.__on_query_tooltip)
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        if self._album.artists:
            artists = GLib.markup_escape_text(", ".join(self._album.artists))
        else:
            artists = _("Compilation")
        self.__artist_label = Gtk.Label.new("<b>%s</b>" % artists)
        self.__artist_label.set_use_markup(True)
        self.__artist_label.set_hexpand(True)
        self.__artist_label.set_property("halign", Gtk.Align.START)
        self.__artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__title_label = Gtk.Label.new(self._album.name)
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__title_label.set_property("halign", Gtk.Align.START)
        self.__title_label.get_style_context().add_class("dim-label")
        self.__action_button = None
        if self._view_type & (ViewType.POPOVER | ViewType.PLAYLISTS):
            self.__action_button = Gtk.Button.new_from_icon_name(
                "list-remove-symbolic",
                Gtk.IconSize.MENU)
            self.__action_button.set_tooltip_text(
                _("Remove from playlist"))
        elif self._album.storage_type & StorageType.EPHEMERAL:
            self.__action_button = Gtk.Button.new_from_icon_name(
                "document-save-symbolic",
                Gtk.IconSize.MENU)
            self.__action_button.set_tooltip_text(_("Save in collection"))
        elif self._view_type & ViewType.SEARCH:
            self.__action_button = Gtk.Button.new_from_icon_name(
                    'avatar-default-symbolic',
                    Gtk.IconSize.MENU)
            self.__action_button.set_tooltip_text(_("Go to artist view"))
        else:
            self.__action_button = Gtk.Button.new_from_icon_name(
                "view-more-symbolic",
                Gtk.IconSize.MENU)
        if self.__action_button is not None:
            self.__action_button.set_margin_end(MARGIN_SMALL)
            self.__action_button.set_relief(Gtk.ReliefStyle.NONE)
            self.__action_button.get_style_context().add_class("menu-button")
            self.__action_button.set_property("valign", Gtk.Align.CENTER)
            self.__gesture_helper = GesturesHelper(
                self.__action_button,
                primary_press_callback=self._on_action_button_press)
        grid.attach(self._artwork, 0, 0, 1, 2)
        grid.attach(self.__artist_label, 1, 0, 1, 1)
        grid.attach(self.__title_label, 1, 1, 1, 1)
        if self.__action_button is not None:
            grid.attach(self.__action_button, 2, 0, 1, 2)
        self.__revealer = Gtk.Revealer.new()
        self.__revealer.show()
        grid.attach(self.__revealer, 0, 2, 3, 1)
        self.add(grid)
        self.set_playing_indicator()
        if self.__reveal or self._view_type & ViewType.PLAYLISTS:
            self.reveal(True)
        self.set_artwork()

    def append_rows(self, tracks):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
        """
        if self._responsive_widget is not None:
            TracksView.append_rows(self, tracks)

    def insert_rows(self, tracks, position):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
            @param position as int
        """
        if self._responsive_widget is not None:
            TracksView.insert_rows(self, tracks, position)

    def reveal(self, reveal=None):
        """
            Reveal/Unreveal tracks
            @param reveal as bool or None to just change state
        """
        if self.__revealer.get_reveal_child() and reveal is not True:
            self.__revealer.set_reveal_child(False)
            if self.album.id == App().player.current_track.album.id:
                self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            if self._responsive_widget is None:
                TracksView.populate(self)
                self._responsive_widget.show()
                self.__revealer.add(self._responsive_widget)
            self.__revealer.set_reveal_child(True)
            self.unset_state_flags(Gtk.StateFlags.VISITED)

    def set_playing_indicator(self):
        """
            Show play indicator
        """
        if self._artwork is None:
            return
        selected = self.album.id == App().player.current_track.album.id and\
            App().player.current_track.id in self.album.track_ids
        if self.__revealer.get_reveal_child():
            TracksView.set_playing_indicator(self)
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)
        elif selected:
            self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def stop(self):
        """
            Stop view loading
        """
        self._artwork = None
        if self._responsive_widget is not None:
            TracksView.stop(self)

    def set_artwork(self):
        """
            Set album artwork
        """
        if self._artwork is None:
            return
        App().art_helper.set_album_artwork(self._album,
                                           ArtSize.SMALL,
                                           ArtSize.SMALL,
                                           self._artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE |
                                           ArtBehaviour.CROP_SQUARE,
                                           self.__on_album_artwork)

    def update_track_position(self, position):
        """
            Update track position based on current tracks
            @param position as int
            @return position as int
        """
        for row in self.children:
            row.set_position(position)
            position += 1
        return position

    @property
    def revealed(self):
        """
            True if revealed
            @return bool
        """
        return self.__revealer is not None and\
            self.__revealer.get_reveal_child()

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return True if self._responsive_widget is None\
            else TracksView.get_populated(self)

    @property
    def name(self):
        """
            Get row name
            @return str
        """
        return self.__title_label.get_text() + self.__artist_label.get_text()

    @property
    def album(self):
        """
            Get album
            @return row id as int
        """
        return self._album

#######################
# PROTECTED           #
#######################
    def _on_tracks_populated(self, disc_number):
        """
            Populate remaining discs
            @param disc_number as int
        """
        if not self.is_populated:
            TracksView.populate(self)
        else:
            self.emit("populated")

    def _on_action_button_press(self, x, y, event):
        """
            Show row menu
            @param x as int
            @param y as int
            @param event as Gdk.EventButton
        """
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            return True
        if self._album.storage_type & StorageType.EPHEMERAL:
            App().art.copy_from_web_to_store(self._album.id)
            App().art.cache_artists_artwork()
            self._album.save(True)
            self.__action_button.hide()
        elif self._view_type & ViewType.SEARCH:
            popover = self.get_ancestor(Gtk.Popover)
            if popover is not None:
                popover.popdown()
            App().window.container.show_view([Type.ARTISTS],
                                             self._album.artist_ids)
        elif self._view_type & ViewType.PLAYLISTS:
            if App().player.current_track.album.id == self._album.id:
                # Stop playback or loop for last album
                # Else skip current
                if len(App().player.albums) == 1:
                    App().player.remove_album(self._album)
                    App().player.next()
                else:
                    App().player.skip_album()
                    App().player.remove_album(self._album)
            else:
                App().player.remove_album(self._album)
            # Remove album from playlists
            # A playlists can't have duplicate so just remove tracks
            if self._view_type & ViewType.PLAYLISTS:
                self.emit("remove-from-playlist", self._album)
            self.destroy()
        else:
            self.__popup_menu(self.__action_button)

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, widget):
        """
            Popup menu for album
            @param widget as Gtk.Widget
        """
        def on_closed(widget):
            self.get_style_context().remove_class("menu-selected")

        from lollypop.menu_objects import AlbumMenu
        menu = AlbumMenu(self._album, ViewType.ALBUM)
        popover = Gtk.Popover.new_from_model(widget, menu)
        popover.connect("closed", on_closed)
        self.get_style_context().add_class("menu-selected")
        popover.popup()

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if self._artwork is None:
            return
        if surface is None:
            self._artwork.set_from_icon_name("folder-music-symbolic",
                                             Gtk.IconSize.BUTTON)
        else:
            self._artwork.set_from_surface(surface)
        self.emit("populated")
        self.show_all()

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self.__title_label.get_layout()
        layout_artist = self.__artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = GLib.markup_escape_text(self.__artist_label.get_text())
            title = GLib.markup_escape_text(self.__title_label.get_text())
            self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
        else:
            self.set_tooltip_text("")

    def __on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()
        self._artwork = None
