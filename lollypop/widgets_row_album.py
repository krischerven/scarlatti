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

from gi.repository import Gtk, Gdk, Gio, GLib, GObject, Pango

from gettext import gettext as _

from lollypop.view_tracks import TracksView
from lollypop.define import ArtSize, App, ViewType, MARGIN_SMALL
from lollypop.define import ArtBehaviour
from lollypop.widgets_row_dnd import DNDRow
from lollypop.logger import Logger


class AlbumRow(Gtk.ListBoxRow, TracksView, DNDRow):
    """
        Album row
    """

    __gsignals__ = {
        "insert-album": (
            GObject.SignalFlags.RUN_FIRST, None,
            (int, GObject.TYPE_PYOBJECT, bool)),
        "insert-track": (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        "insert-album-after": (GObject.SignalFlags.RUN_FIRST, None,
                               (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "remove-album": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "remove-from-playlist": (GObject.SignalFlags.RUN_FIRST, None,
                                 (GObject.TYPE_PYOBJECT,)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "do-selection": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "track-activated": (GObject.SignalFlags.RUN_FIRST, None,
                            (GObject.TYPE_PYOBJECT,))
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
        cover_height = AlbumRow.__MARGIN * 2 + ArtSize.MEDIUM
        if font_height > cover_height:
            return font_height + 2
        else:
            return cover_height + 2

    def __init__(self, album, height, view_type,
                 reveal, cover_uri, parent, position):
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
        TracksView.__init__(self, view_type, position)
        if view_type & ViewType.DND:
            DNDRow.__init__(self)
        self.__next_row = None
        self.__previous_row = None
        self.__revealer = None
        self.__parent = parent
        self.__reveal = reveal
        self.__cover_uri = cover_uri
        self._artwork = None
        self._album = album
        self.__view_type = view_type
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
                                   ArtSize.MEDIUM, ArtSize.MEDIUM)
        self._artwork.set_margin_start(self.__MARGIN)
        # Little hack: we do not set margin_bottom because already set by
        # get_best_height(): we are Align.FILL
        # This allow us to not Align.CENTER row_widget and not jump up
        # and down on reveal()
        self._artwork.set_margin_top(self.__MARGIN)
        self.get_style_context().add_class("albumrow")
        self.set_sensitive(True)
        self.set_selectable(False)
        self.set_property("has-tooltip", True)
        self.connect("query-tooltip", self.__on_query_tooltip)
        self.__row_widget = Gtk.EventBox()
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
        if self.__view_type & (ViewType.POPOVER | ViewType.PLAYLISTS):
            self.__action_button = Gtk.Button.new_from_icon_name(
                "list-remove-symbolic",
                Gtk.IconSize.MENU)
            self.__action_button.set_tooltip_text(
                _("Remove from playlist"))
        elif self._album.mtime == 0:
            self.__action_button = Gtk.Button.new_from_icon_name(
                "document-save-symbolic",
                Gtk.IconSize.MENU)
            self.__action_button.set_tooltip_text(_("Save in collection"))
        elif self.__view_type & ViewType.SEARCH:
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
            self.__action_button.get_style_context().add_class(
                "album-menu-button")
            self.__action_button.get_style_context().add_class(
                "track-menu-button")
            self.__action_button.set_property("valign", Gtk.Align.CENTER)
            self.__action_button.connect("button-release-event",
                                         self.__on_action_button_release_event)
        grid.attach(self._artwork, 0, 0, 1, 2)
        grid.attach(self.__artist_label, 1, 0, 1, 1)
        grid.attach(self.__title_label, 1, 1, 1, 1)
        if self.__action_button is not None:
            grid.attach(self.__action_button, 2, 0, 1, 2)
        self.__revealer = Gtk.Revealer.new()
        self.__revealer.show()
        grid.attach(self.__revealer, 0, 2, 3, 1)
        self.__row_widget.add(grid)
        self.add(self.__row_widget)
        self.set_playing_indicator()
        self.__gesture = Gtk.GestureLongPress.new(self.__row_widget)
        self.__gesture.connect("pressed", self.__on_gesture_pressed)
        self.__gesture.connect("end", self.__on_gesture_end)
        # We want to get release event after gesture
        self.__gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.__gesture.set_button(0)
        if self.__reveal or self.__view_type & ViewType.PLAYLISTS:
            self.reveal(True)
        if self.__cover_uri is None:
            self.set_artwork()
        else:
            self.__on_album_artwork(None)
            App().task_helper.load_uri_content(self.__cover_uri,
                                               self.__cancellable,
                                               self.__on_cover_uri_content)

    def append_rows(self, tracks):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
        """
        if self._responsive_widget is not None:
            TracksView.append_rows(self, tracks)

    def prepend_rows(self, tracks):
        """
            Add track rows (only works for albums with merged discs)
            @param tracks as [Track]
        """
        if self._responsive_widget is not None:
            TracksView.prepend_rows(self, tracks)

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
        selected = self.album.id == App().player.current_track.album.id
        if self.__revealer.get_reveal_child():
            TracksView.set_playing_indicator(self)
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)
        elif selected:
            self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            self.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def update_tracks_position(self, position):
        """
            Update tracks position
            @param position as int
            @return new position
        """
        self.__position = position
        for child in self.children:
            child.set_position(self.__position)
            self.__position += 1
        return self.__position

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
                                           ArtSize.MEDIUM,
                                           ArtSize.MEDIUM,
                                           self._artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE |
                                           ArtBehaviour.CROP_SQUARE,
                                           self.__on_album_artwork)

    def set_next_row(self, row):
        """
            Set next row
            @param row as Row
        """
        self.__next_row = row

    def set_previous_row(self, row):
        """
            Set previous row
            @param row as Row
        """
        self.__previous_row = row

    @property
    def next_row(self):
        """
            Get next row
            @return row as Row
        """
        return self.__next_row

    @property
    def previous_row(self):
        """
            Get previous row
            @return row as Row
        """
        return self.__previous_row

    @property
    def parent(self):
        """
            Get parent view
            @return AlbumListView
        """
        return self.__parent

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return True if self._responsive_widget is None\
            else TracksView.get_populated(self)

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

    def _on_activated(self, widget, track):
        """
            A row has been activated, play track
            if in playlist, pass signal
            @param widget as TracksWidget
            @param track as Track
        """
        if self._view_type & ViewType.PLAYLISTS:
            self.emit("track-activated", track)
        else:
            TracksView._on_activated(self, widget, track)

#######################
# PRIVATE             #
#######################
    def __popup_menu(self, widget, xcoordinate=None, ycoordinate=None):
        """
            Popup menu for album
            @param eventbox as Gtk.EventBox
            @param xcoordinate as int (or None)
            @param ycoordinate as int (or None)
        """
        def on_closed(widget):
            self.get_style_context().remove_class("track-menu-selected")

        from lollypop.menu_objects import AlbumMenu
        menu = AlbumMenu(self._album, ViewType.ALBUM)
        popover = Gtk.Popover.new_from_model(widget, menu)
        popover.connect("closed", on_closed)
        self.get_style_context().add_class("track-menu-selected")
        if xcoordinate is not None and ycoordinate is not None:
            rect = Gdk.Rectangle()
            rect.x = xcoordinate
            rect.y = ycoordinate
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
        popover.popup()

    def __on_cover_uri_content(self, uri, status, data):
        """
            Save to tmp cache
            @param uri as str
            @param status as bool
            @param data as bytes
        """
        try:
            if status:
                App().art.save_album_artwork(data, self._album)
                self.set_artwork()
        except Exception as e:
            Logger.error("AlbumRow::__on_cover_uri_content(): %s", e)

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

    def __on_gesture_pressed(self, gesture, x, y):
        """
            Show menu
            @param gesture as Gtk.GestureLongPress
            @param x as float
            @param y as float
        """
        self.__popup_menu(self, x, y)

    def __on_gesture_end(self, gesture, sequence):
        """
            Connect button release event
            Here because we only want this if a gesture was recognized
            This allow touch scrolling
        """
        self.__row_widget.connect("button-release-event",
                                  self.__on_button_release_event)

    def __on_button_release_event(self, widget, event):
        """
            Handle button release event
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        widget.disconnect_by_func(self.__on_button_release_event)
        if event.state & Gdk.ModifierType.CONTROL_MASK and\
                self.__view_type & ViewType.DND:
            if self.get_state_flags() & Gtk.StateFlags.SELECTED:
                self.set_state_flags(Gtk.StateFlags.NORMAL, True)
            else:
                self.set_state_flags(Gtk.StateFlags.SELECTED, True)
        elif event.state & Gdk.ModifierType.SHIFT_MASK and\
                self.__view_type & ViewType.DND:
            self.emit("do-selection")
        elif event.button == 1:
            if self.__view_type & ViewType.PLAYLISTS and self._album.tracks:
                track = self._album.tracks[0]
                self.emit("track-activated", track)
            else:
                self.reveal()
        elif event.button == 3:
            self.__popup_menu(self, event.x, event.y)
        return True

    def __on_action_button_release_event(self, button, event):
        """
            Handle button actions
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            return True
        if self._album.mtime == 0:
            App().art.copy_from_web_to_store(self._album.id)
            App().art.cache_artists_artwork()
            self._album.save(True)
            self.destroy()
        elif self.__view_type & ViewType.SEARCH:
            popover = self.get_ancestor(Gtk.Popover)
            if popover is not None:
                popover.popdown()
            App().window.container.show_artist_view(self._album.artist_ids)
        elif self.__view_type & (ViewType.POPOVER | ViewType.PLAYLISTS):
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
            if self.__view_type & ViewType.PLAYLISTS:
                self.emit("remove-from-playlist", self._album)
            self.destroy()
        else:
            self.__popup_menu(button)
        return True

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
