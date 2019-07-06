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

from lollypop.utils import get_icon_name
from lollypop.view_tracks import TracksView
from lollypop.view import LazyLoadingView
from lollypop.objects import Album, Track
from lollypop.define import ArtSize, App, ViewType, MARGIN, MARGIN_SMALL, Type
from lollypop.define import ArtBehaviour
from lollypop.controller_view import ViewController, ViewControllerType
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
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "do-selection": (GObject.SignalFlags.RUN_FIRST, None, ())
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

    def __init__(self, album, height, view_type, reveal, cover_uri, parent):
        """
            Init row widgets
            @param album as Album
            @param height as int
            @param view_type as ViewType
            @param reveal as bool
            @param parent as AlbumListView
        """
        Gtk.ListBoxRow.__init__(self)
        TracksView.__init__(self, view_type)
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
        if self.__view_type & ViewType.DND:
            self.__action_button = Gtk.Button.new_from_icon_name(
                "list-remove-symbolic",
                Gtk.IconSize.MENU)
            self.__action_button.set_tooltip_text(
                _("Remove from current playlist"))
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
        elif not self.__view_type & ViewType.POPOVER:
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
        if self.__reveal:
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
            self.get_style_context().remove_class("albumrow-hover")
            if self.album.id == App().player.current_track.album.id:
                self.set_state_flags(Gtk.StateFlags.VISITED, True)
        else:
            if self._responsive_widget is None:
                TracksView.populate(self)
                self._responsive_widget.show()
                self.__revealer.add(self._responsive_widget)
            self.__revealer.set_reveal_child(True)
            self.unset_state_flags(Gtk.StateFlags.VISITED)
            self.get_style_context().add_class("albumrow-hover")

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
        return True if self._responsive_widget is None or self.__reveal\
            else TracksView.get_populated(self)

    def set_filtered(self, b):
        """
            Set widget filtered
            @param b as bool
            @return bool (should be shown)
        """
        self.__filtered = b
        return not b

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__filtered

    @property
    def filter(self):
        """
            @return str
        """
        return " ".join([self._album.name] + self._album.artists)

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
        elif self.__view_type & ViewType.DND:
            if App().player.current_track.album.id == self._album.id:
                # If not last album, skip it
                if len(App().player.albums) > 1:
                    App().player.skip_album()
                    App().player.remove_album(self._album)
                # remove it and stop playback by going to next track
                else:
                    App().player.remove_album(self._album)
                    App().player.stop()
            else:
                App().player.remove_album(self._album)
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


class AlbumsListView(LazyLoadingView, ViewController):
    """
        View showing albums
    """

    def __init__(self, genre_ids, artist_ids, view_type):
        """
            Init widget
            @param genre_ids as int
            @param artist_ids as int
            @param view_type as ViewType
        """
        LazyLoadingView.__init__(self, view_type | ViewType.FILTERED)
        ViewController.__init__(self, ViewControllerType.ALBUM)
        self.__genre_ids = genre_ids
        self.__artist_ids = artist_ids
        if genre_ids and genre_ids[0] < 0:
            if genre_ids[0] == Type.WEB and\
                    GLib.find_program_in_path("youtube-dl") is None:
                self._empty_message = _("Missing youtube-dl command")
            self._empty_icon_name = get_icon_name(genre_ids[0])
        self.__autoscroll_timeout_id = None
        self.__reveals = []
        self.__prev_animated_rows = []
        # Calculate default album height based on current pango context
        # We may need to listen to screen changes
        self.__height = AlbumRow.get_best_height(self)
        self._box = Gtk.ListBox()
        self._box.set_margin_end(MARGIN)
        self._box.get_style_context().add_class("trackswidget")
        self._box.set_vexpand(True)
        self._box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.set_activate_on_single_click(True)
        self._box.set_filter_func(self._filter_func)
        self._box.show()
        self._scrolled.set_property("expand", True)
        self.add(self._scrolled)

    def set_reveal(self, albums):
        """
            Set albums to reveal on populate
            @param albums as [Album]
        """
        self.__reveals = albums

    def insert_album(self, album, reveal, position, cover_uri=None):
        """
            Add an album
            @param album as Album
            @param reveal as bool
            @param position as int
            @param cover_uri as str
        """
        row = self.__row_for_album(album, reveal, cover_uri)
        children = self._box.get_children()
        if children:
            previous_row = children[position]
            row.set_previous_row(previous_row)
            previous_row.set_next_row(row)
        row.populate()
        row.show()
        self._box.insert(row, position)
        if self._viewport.get_child() is None:
            self._viewport.add(self._box)

    def populate(self, albums):
        """
            Populate widget with album rows
            @param albums as [Album]
        """
        if albums:
            self._lazy_queue = []
            for child in self._box.get_children():
                GLib.idle_add(child.destroy)
            self.__add_albums(list(albums))
        else:
            LazyLoadingView.populate(self)

    def rows_animation(self, x, y):
        """
            Show animation to help user dnd
            @param x as int
            @param y as int
        """
        # FIXME autoscroll continue after drop
        self.clear_animation()
        for row in self._box.get_children():
            coordinates = row.translate_coordinates(self, 0, 0)
            if coordinates is None:
                continue
            (row_x, row_y) = coordinates
            row_width = row.get_allocated_width()
            row_height = row.get_allocated_height()
            if x < row_x or\
                    x > row_x + row_width or\
                    y < row_y or\
                    y > row_y + row_height:
                continue
            if y <= row_y + ArtSize.MEDIUM / 2:
                self.__prev_animated_rows.append(row)
                row.get_style_context().add_class("drag-up")
                break
            elif y >= row_y + row_height - ArtSize.MEDIUM / 2:
                self.__prev_animated_rows.append(row)
                row.get_style_context().add_class("drag-down")
                GLib.timeout_add(1000, self.__reveal_row, row)
                break
            else:
                subrow = row.rows_animation(x, y, self)
                if subrow is not None:
                    self.__prev_animated_rows.append(subrow)

    def clear_animation(self):
        """
            Clear any animation
        """
        for row in self.__prev_animated_rows:
            ctx = row.get_style_context()
            ctx.remove_class("drag-up")
            ctx.remove_class("drag-down")

    def jump_to_current(self):
        """
            Scroll to album
        """
        y = self.__get_current_ordinate()
        if y is not None:
            self._scrolled.get_vadjustment().set_value(y)

    def clear(self, clear_albums=False):
        """
            Clear the view
        """
        for child in self._box.get_children():
            GLib.idle_add(child.destroy)
        if clear_albums:
            App().player.clear_albums()

    @property
    def children(self):
        """
            Get view children
            @return [AlbumRow]
        """
        return self._box.get_children()

#######################
# PROTECTED           #
#######################
    def _on_current_changed(self, player):
        """
            Update children state
            @param player as Player
        """
        for child in self._box.get_children():
            child.set_playing_indicator()

    def _on_artwork_changed(self, artwork, album_id):
        """
            Update children artwork if matching album id
            @param artwork as Artwork
            @param album_id as int
        """
        for child in self._box.get_children():
            if child.album.id == album_id:
                child.set_artwork()

    def _on_duration_changed(self, player, track_id):
        """
            Update track duration
            @param player as Player
            @param track_id as int
        """
        for child in self.children:
            child.update_duration(track_id)

    def _on_album_updated(self, scanner, album_id, added):
        """
            Handles changes in collection
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        if self._view_type & (ViewType.SEARCH | ViewType.DND):
            return
        if added:
            album_ids = App().window.container.get_view_album_ids(
                                            self.__genre_ids,
                                            self.__artist_ids)
            if album_id not in album_ids:
                return
            index = album_ids.index(album_id)
            self.insert_album(Album(album_id), False, index)
        else:
            for child in self._box.get_children():
                if child.album.id == album_id:
                    child.destroy()

    def _on_map(self, widget):
        """
            Connect signals and set active ids
            @param widget as Gtk.Widget
        """
        LazyLoadingView._on_map(self, widget)
        if not self.__genre_ids and not self.__artist_ids:
            return
        if self.__genre_ids:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__genre_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", self.__artist_ids))
        else:
            App().settings.set_value("state-one-ids",
                                     GLib.Variant("ai", self.__artist_ids))
            App().settings.set_value("state-two-ids",
                                     GLib.Variant("ai", []))
        App().settings.set_value("state-three-ids",
                                 GLib.Variant("ai", []))

#######################
# PRIVATE             #
#######################
    def __reveal_row(self, row):
        """
            Reveal row if style always present
        """
        style_context = row.get_style_context()
        if style_context.has_class("drag-down"):
            row.reveal(True)

    def __add_albums(self, albums, previous_row=None):
        """
            Add items to the view
            @param albums ids as [Album]
            @param previous_row as AlbumRow
        """
        if self._lazy_queue is None or self._viewport is None:
            return
        if albums:
            album = albums.pop(0)
            row = self.__row_for_album(album, album in self.__reveals)
            row.set_previous_row(previous_row)
            if previous_row is not None:
                previous_row.set_next_row(row)
            row.show()
            self._box.add(row)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_albums, albums, row)
        else:
            # If only one album, we want to reveal it
            # Stop lazy loading and populate
            children = self._box.get_children()
            if len(children) == 1:
                self.stop()
                children[0].populate()
                children[0].reveal(True)
            else:
                self.lazy_loading()
            if self._viewport.get_child() is None:
                self._viewport.add(self._box)

    def __row_for_album(self, album, reveal=False, cover_uri=None):
        """
            Get a row for track id
            @param album as Album
            @param reveal as bool
            @param cover_uri as str
        """
        row = AlbumRow(album, self.__height, self._view_type,
                       reveal, cover_uri, self)
        row.connect("insert-track", self.__on_insert_track)
        row.connect("insert-album", self.__on_insert_album)
        row.connect("insert-album-after", self.__on_insert_album_after)
        row.connect("remove-album", self.__on_remove_album)
        row.connect("do-selection", self.__on_do_selection)
        return row

    def __auto_scroll(self, up):
        """
            Auto scroll up/down
            @param up as bool
        """
        adj = self._scrolled.get_vadjustment()
        value = adj.get_value()
        if up:
            adj_value = value - ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() == 0:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().add_class("drag-up")
        else:
            adj_value = value + ArtSize.SMALL
            adj.set_value(adj_value)
            if adj.get_value() < adj_value:
                self.__autoscroll_timeout_id = None
                self.get_style_context().remove_class("drag-down")
                self.get_style_context().remove_class("drag-up")
                return False
            else:
                self.get_style_context().add_class("drag-down")
                self.get_style_context().remove_class("drag-up")
        return True

    def __get_current_ordinate(self):
        """
            If current track in widget, return it ordinate,
            @return y as int
        """
        y = None
        for child in self._box.get_children():
            if child.album == App().player.current_track.album:
                child.populate()
                child.reveal(True)
                y = child.translate_coordinates(self._box, 0, 0)[1]
        return y

    def __on_insert_track(self, row, new_track_id, down):
        """
            Insert a new row at position
            @param row as PlaylistRow
            @param new_track_id as int
            @param down as bool
        """
        new_track = Track(new_track_id)
        children = self._box.get_children()
        position = children.index(row)
        lenght = len(children)
        if down:
            position += 1
        # Append track to current/next album
        if position < lenght and\
                children[position].album.id == new_track.album.id:
            new_track.set_album(children[position].album)
            children[position].prepend_rows([new_track])
            children[position].album.insert_track(new_track, 0)
        # Append track to previous/current album
        elif position - 1 < lenght and\
                children[position - 1].album.id == new_track.album.id:
            new_track.set_album(children[position - 1].album)
            children[position - 1].append_rows([new_track])
            children[position - 1].album.insert_track(new_track)
        # Add a new album
        else:
            album = Album(new_track.album.id)
            album.set_tracks([new_track])
            new_row = self.__row_for_album(album)
            new_row.populate()
            new_row.show()
            self._box.insert(new_row, position)
            App().player.add_album(album, position)
            if row.previous_row is not None and\
                    row.previous_row.album.id ==\
                    App().player.current_track.album.id:
                App().player.set_next()
                App().player.set_prev()

    def __on_insert_album(self, row, new_album_id, track_ids, down):
        """
            Insert a new row at position
            @param row as AlbumRow
            @param new_track_id as int
            @param track_ids as [int]
            @param down as bool
        """
        position = self._box.get_children().index(row)
        if down:
            position += 1
        album = Album(new_album_id)
        album.set_tracks([Track(track_id) for track_id in track_ids])
        new_row = self.__row_for_album(album)
        new_row.populate()
        new_row.show()
        self._box.insert(new_row, position)
        App().player.add_album(album, position)

    def __on_insert_album_after(self, view, after_album, album):
        """
            Insert album after after_album
            @param view as TracksView
            @param after_album as Album
            @param album as Album
        """
        position = 0
        children = self._box.get_children()
        # If after_album is undefined, prepend)
        if after_album.id is not None:
            for row in children:
                if row.album == after_album:
                    break
                position += 1
        new_row = self.__row_for_album(album)
        new_row.populate()
        new_row.set_previous_row(children[position])
        new_row.set_next_row(children[position].next_row)
        children[position].set_next_row(new_row)
        if new_row.next_row is not None:
            new_row.next_row.set_previous_row(new_row)
        new_row.show()
        self._box.insert(new_row, position + 1)
        App().player.add_album(album, position + 1)

    def __on_remove_album(self, row):
        """
            Remove album from player
            @param row as AlbumRow
        """
        App().player.remove_album(row.album)

    def __on_do_selection(self, row):
        """
            Select rows from start (or any selected row) to track
            @param row as AlbumRow
        """
        children = self._box.get_children()
        selected = None
        end = children.index(row) + 1
        for child in children:
            if child == row:
                break
            if child.get_state_flags() & Gtk.StateFlags.SELECTED:
                selected = child
        if selected is None:
            start = 0
        else:
            start = children.index(selected)
        for child in children[start:end]:
            child.set_state_flags(Gtk.StateFlags.SELECTED, True)
        for child in children[end:]:
            child.set_state_flags(Gtk.StateFlags.NORMAL, True)
