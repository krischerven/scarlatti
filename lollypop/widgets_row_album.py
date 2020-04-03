# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.view_tracks_album import AlbumTracksView
from lollypop.define import ArtSize, App, ViewType, MARGIN_SMALL
from lollypop.define import ArtBehaviour, StorageType
from lollypop.utils import popup_widget, emit_signal
from lollypop.helper_gestures import GesturesHelper
from lollypop.helper_signals import SignalsHelper, signals_map


class AlbumRow(Gtk.ListBoxRow, SignalsHelper):
    """
        Album row
    """

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST,
                      None, (GObject.TYPE_PYOBJECT,)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def get_best_height(widget):
        """
            Helper to pass object it's height request
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(MARGIN_SMALL * 2 +
                          2 * layout.get_pixel_size()[1])
        cover_height = MARGIN_SMALL * 2 + ArtSize.SMALL
        # Don't understand what is this magic value
        # May not work properly without Adwaita
        if font_height > cover_height:
            return font_height + 4
        else:
            return cover_height + 4

    @signals_map
    def __init__(self, album, height, view_type):
        """
            Init row widgets
            @param album as Album
            @param height as int
            @param view_type as ViewType
            @param parent as AlbumListView
        """
        Gtk.ListBoxRow.__init__(self)
        self.__view_type = view_type
        self.__revealer = None
        self.__artwork = None
        self.__gesture_list = None
        self.__album = album
        self.__cancellable = Gio.Cancellable()
        self.set_sensitive(False)
        context_style = self.get_style_context()
        context_style.add_class("albumrow")
        context_style.add_class("albumrow-collapsed")
        self.set_property("height-request", height)
        self.connect("destroy", self.__on_destroy)
        self.__tracks_view = self.__get_track_view()
        return [
            (App().player, "playback-added", "_on_playback_changed"),
            (App().player, "playback-updated", "_on_playback_changed"),
            (App().player, "playback-removed", "_on_playback_changed")
        ]

    def populate(self):
        """
            Populate widget content
        """
        if self.__artwork is not None:
            self.emit("populated")
            return
        self.__artwork = Gtk.Image.new()
        App().art_helper.set_frame(self.__artwork, "small-cover-frame",
                                   ArtSize.SMALL, ArtSize.SMALL)
        self.set_sensitive(True)
        self.set_property("has-tooltip", True)
        self.connect("query-tooltip", self.__on_query_tooltip)
        if self.__album.artists:
            artists = GLib.markup_escape_text(", ".join(self.__album.artists))
        else:
            artists = _("Compilation")
        self.__artist_label = Gtk.Label.new("<b>%s</b>" % artists)
        self.__artist_label.set_use_markup(True)
        self.__artist_label.set_property("halign", Gtk.Align.START)
        self.__artist_label.set_hexpand(True)
        self.__artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__title_label = Gtk.Label.new(self.__album.name)
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__title_label.set_property("halign", Gtk.Align.START)
        self.__title_label.get_style_context().add_class("dim-label")
        buttons = []
        if self.__view_type & ViewType.SEARCH:
            button = Gtk.Button.new_from_icon_name(
                    "media-playback-start-symbolic",
                    Gtk.IconSize.MENU)
            button.set_tooltip_text(_("Play this album"))
            self.__gesture_play = GesturesHelper(
                button,
                primary_press_callback=self.__on_play_button_press)
            buttons.append(button)
            if self.__album.storage_type & StorageType.EPHEMERAL:
                button = Gtk.Button.new_from_icon_name(
                    "document-save-symbolic", Gtk.IconSize.MENU)
                button.set_tooltip_text(_("Save in collection"))
                self.__gesture_save = GesturesHelper(
                    button,
                    primary_press_callback=self.__on_save_button_press)
                buttons.append(button)
        if self.__view_type & (ViewType.PLAYBACK |
                               ViewType.PLAYLISTS |
                               ViewType.SEARCH):
            button = Gtk.Button()
            image = Gtk.Image.new()
            button.set_image(image)
            self.__update_list_button(button)
            self.__gesture_list = GesturesHelper(
                button,
                primary_press_callback=self.__on_list_button_press)
            buttons.append(button)

        header = Gtk.Grid.new()
        header.set_column_spacing(MARGIN_SMALL)
        header.show()
        header.set_margin_start(MARGIN_SMALL)
        # 2px for trackrow padding
        header.set_margin_end(MARGIN_SMALL + 2)
        header.set_margin_top(2)
        header.set_margin_bottom(2)
        header.attach(self.__artwork, 0, 0, 1, 2)
        header.attach(self.__artist_label, 1, 0, 1, 1)
        header.attach(self.__title_label, 1, 1, 1, 1)
        i = 2
        for button in buttons:
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class("menu-button")
            button.set_property("valign", Gtk.Align.CENTER)
            header.attach(button, i, 0, 1, 2)
            i += 1

        self.__revealer = Gtk.Revealer.new()
        self.__revealer.show()
        self.__revealer.add(self.__tracks_view)

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        box.pack_start(header, 0, True, True)
        box.pack_start(self.__revealer, 1, False, False)
        self.add(box)
        self.set_playing_indicator()
        self.set_artwork()

    def reveal(self, reveal=None):
        """
            Reveal/Unreveal tracks
            @param reveal as bool or None to just change state
        """
        if self.__artwork is None:
            self.populate()
        if self.__revealer.get_reveal_child() and reveal is not True:
            self.__revealer.set_reveal_child(False)
            self.get_style_context().add_class("albumrow-collapsed")
            if self.album.id == App().player.current_track.album.id:
                self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            if not self.__tracks_view.is_populated:
                self.__tracks_view.populate()
            self.__revealer.set_reveal_child(True)
            self.get_style_context().remove_class("albumrow-collapsed")
            self.unset_state_flags(Gtk.StateFlags.VISITED)

    def set_playing_indicator(self):
        """
            Show play indicator
        """
        if self.__artwork is None:
            return
        selected = self.album.id == App().player.current_track.album.id and\
            App().player.current_track.id in self.album.track_ids
        if self.__revealer.get_reveal_child():
            self.__tracks_view.set_playing_indicator()
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)
        elif selected:
            self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def stop(self):
        """
            Stop view loading
        """
        self.__artwork = None
        if self.__tracks_view.is_populated:
            self.__tracks_view.stop()

    def reset(self):
        """
            Get a new track view
        """
        self.stop()
        self.__tracks_view.destroy()
        self.__tracks_view = self.__get_tracks_view()
        self.__revealer.add(self.__tracks_view)

    def set_artwork(self):
        """
            Set album artwork
        """
        if self.__artwork is None:
            return
        App().art_helper.set_album_artwork(self.__album,
                                           ArtSize.SMALL,
                                           ArtSize.SMALL,
                                           self.__artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE |
                                           ArtBehaviour.CROP_SQUARE,
                                           self.__on_album_artwork)

    @property
    def revealed(self):
        """
            True if revealed
            @return bool
        """
        return self.__revealer is not None and\
            self.__revealer.get_reveal_child()

    @property
    def tracks_view(self):
        """
            Get tracks view
            @return TracksView
        """
        return self.__tracks_view

    @property
    def listbox(self):
        """
            Get listbox
            @return Gtk.ListBox
        """
        if self.__tracks_view.boxes:
            return self.__tracks_view.boxes[0]
        else:
            return Gtk.ListBox.new()

    @property
    def children(self):
        """
            Get track rows
            @return [TrackRow]
        """
        if self.__tracks_view.boxes:
            return self.__tracks_view.boxes[0].get_children()
        else:
            return []

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return not self.revealed or self.__tracks_view.is_populated

    @property
    def name(self):
        """
            Get row name
            @return str
        """
        if self.__artwork is None:
            return ""
        else:
            return self.__title_label.get_text() +\
                self.__artist_label.get_text()

    @property
    def album(self):
        """
            Get album
            @return row id as int
        """
        return self.__album

#######################
# PROTECTED           #
#######################
    def _on_playback_changed(self, *ignore):
        """
            Update button state
        """
        if self.__artwork is not None and self.__gesture_list is not None:
            self.__update_list_button(self.__gesture_list.widget)

#######################
# PRIVATE             #
#######################
    def __get_track_view(self):
        """
            Get a new track view
            @return AlbumTracksView
        """
        tracks_view = AlbumTracksView(self.__album,
                                      self.__view_type |
                                      ViewType.SINGLE_COLUMN)
        tracks_view.connect("activated",
                            self.__on_tracks_view_activated)
        tracks_view.connect("populated",
                            self.__on_tracks_view_populated)
        tracks_view.connect("track-removed",
                            self.__on_tracks_view_track_removed)
        tracks_view.show()
        return tracks_view

    def __update_list_button(self, button):
        """
            Update list button based on current status
            @param button as Gtk.Button
        """
        if self.__view_type & ViewType.SEARCH and\
                self.__album.id not in App().player.album_ids:
            button.get_image().set_from_icon_name("list-add-symbolic",
                                                  Gtk.IconSize.MENU)
            button.set_tooltip_text(_("Add to playback"))
        else:
            button.get_image().set_from_icon_name("list-remove-symbolic",
                                                  Gtk.IconSize.MENU)
            if self.__view_type & ViewType.PLAYLISTS:
                button.set_tooltip_text(_("Remove from playlist"))
            else:
                button.set_tooltip_text(_("Remove from playback"))

    def __popup_menu(self, widget):
        """
            Popup menu for album
            @param widget as Gtk.Widget
        """
        def on_hidden(popover, hide):
            self.unset_state_flags(Gtk.StateFlags.CHECKED)

        from lollypop.menu_objects import AlbumMenu
        from lollypop.widgets_menu import MenuBuilder
        menu = AlbumMenu(self.__album, ViewType.ALBUM,
                         App().window.is_adaptive)
        menu_widget = MenuBuilder(menu)
        menu_widget.show()
        self.set_state_flags(Gtk.StateFlags.CHECKED, True)
        popover = popup_widget(menu_widget, widget)
        if popover is not None:
            popover.connect("hidden", on_hidden)

    def __on_album_artwork(self, surface):
        """
            Set album artwork
            @param surface as str
        """
        if self.__artwork is None:
            return
        if surface is None:
            self.__artwork.set_from_icon_name("folder-music-symbolic",
                                              Gtk.IconSize.BUTTON)
        else:
            self.__artwork.set_from_surface(surface)
            del surface
        self.show_all()
        # TracksView will emit populated
        if not self.revealed:
            emit_signal(self, "populated")

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
            # Workaround a recent issue in GTK+ 3.24.11
            # self.set_tooltip_markup("<b>%s</b>\n%s" % (artist, title))
            self.set_tooltip_markup("<b>%s</b> - %s" % (artist, title))
        else:
            self.set_tooltip_text("")

    def __on_destroy(self, widget):
        """
            Destroyed widget
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()
        self.__artwork = None

    def __on_tracks_view_activated(self, view, track):
        """
            Pass signal
        """
        emit_signal(self, "activated", track)

    def __on_tracks_view_track_removed(self, view, row):
        """
            Remove row
            @param view as TracksView
            @param row as TrackRow
        """
        row.destroy()
        if len(self.children) == 0:
            App().player.remove_album(self.__album)
            self.destroy()

    def __on_tracks_view_populated(self, view):
        """
            Populate remaining discs
            @param view as TracksView
            @param disc_number as int
        """
        if self.revealed and not self.__tracks_view.is_populated:
            self.__tracks_view.populate()
        else:
            emit_signal(self, "populated")

    def __on_list_button_press(self, x, y, event):
        """
            Add/Remove album from playlist/playback
            @param x as int
            @param y as int
            @param event as Gdk.EventButton
        """
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            return True
        if self.__view_type & (ViewType.PLAYBACK | ViewType.SEARCH):
            if self.__album.id in App().player.album_ids:
                App().player.remove_album(self.__album)
            else:
                App().player.add_album(self.__album)
            if self.__view_type & ViewType.PLAYBACK:
                self.destroy()
            else:
                self.__update_list_button(self.__gesture_list.widget)
        elif self.__view_type & ViewType.PLAYLISTS:
            if App().player.current_track.album.id == self.__album.id:
                # Stop playback or loop for last album
                # Else skip current
                if len(App().player.albums) == 1:
                    App().player.remove_album(self.__album)
                    App().player.next()
                else:
                    App().player.skip_album()
                    App().player.remove_album(self.__album)
            else:
                App().player.remove_album(self.__album)
            from lollypop.view_playlists import PlaylistsView
            view = self.get_ancestor(PlaylistsView)
            if view is not None:
                view.remove_from_playlist(self.__album)
            self.destroy()

    def __on_save_button_press(self, x, y, event):
        """
            Show row menu
            @param x as int
            @param y as int
            @param event as Gdk.EventButton
        """
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            return True
        if self.__album.storage_type & StorageType.EPHEMERAL:
            for artist in self.__album.artists:
                App().art.cache_artist_artwork(artist)
            self.__album.save(True)
            self.__gesture_save.widget.set_sensitive(False)

    def __on_play_button_press(self, x, y, event):
        """
            Show row menu
            @param x as int
            @param y as int
            @param event as Gdk.EventButton
        """
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            return True
        App().player.play_album(self.__album)

    def __on_menu_button_press(self, x, y, event):
        """
            Show row menu
            @param x as int
            @param y as int
            @param event as Gdk.EventButton
        """
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            return True
        self.__popup_menu(self.__gesture_menu.widget)
