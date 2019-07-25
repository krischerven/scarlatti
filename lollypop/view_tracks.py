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

from gi.repository import GLib, Gtk, Gdk, Gio, GObject, Pango

from gettext import gettext as _
from collections import OrderedDict

from lollypop.widgets_tracks import TracksWidget
from lollypop.widgets_row_track import TrackRow
from lollypop.objects_album import Album
from lollypop.logger import Logger
from lollypop.helper_signals import SignalsHelper, signals
from lollypop.utils import get_position_list, set_cursor_hand2
from lollypop.define import App, Type, ViewType, AdaptiveSize


class TracksView(SignalsHelper):
    """
        Responsive view showing discs on one or two rows
        Need to be inherited by an Album widget (AlbumListView, AlbumWidget)
    """
    __gsignals__ = {
        "album-added": (GObject.SignalFlags.RUN_FIRST, None,
                        (int, GObject.TYPE_PYOBJECT)),
        "album-moved": (GObject.SignalFlags.RUN_FIRST, None,
                        (int, GObject.TYPE_PYOBJECT)),
        "track-append": (GObject.SignalFlags.RUN_FIRST, None,
                         (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "track-removed": (GObject.SignalFlags.RUN_FIRST, None,
                          (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        "insert-album-after": (GObject.SignalFlags.RUN_FIRST, None,
                               (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))
    }

    @signals
    def __init__(self, window, position=0):
        """
            Init view
            @param window as AdaptiveWindow/None
            @param initial position as int
        """
        self.__discs = []
        self.__position = position
        self._responsive_widget = None
        self.__orientation = None
        self.__populated = False
        self.__cancellable = Gio.Cancellable()

        if window is None:
            # Calling set_orientation() is needed
            return []
        if App().settings.get_value("force-single-column") or\
                not self._view_type & ViewType.TWO_COLUMNS:
            self.connect("realize",
                         self.__on_realize,
                         window,
                         Gtk.Orientation.VERTICAL)
            return []
        else:
            self.connect("realize",
                         self.__on_realize,
                         window,
                         Gtk.Orientation.HORIZONTAL)
            return [
                (window, "adaptive-size-changed", "_on_adaptive_size_changed")
            ]

    def set_playing_indicator(self):
        """
            Set playing indicator
        """
        try:
            for disc in self.__discs:
                self._tracks_widget_left[disc.number].update_playing(
                    App().player.current_track.id)
                self._tracks_widget_right[disc.number].update_playing(
                    App().player.current_track.id)
        except Exception as e:
            Logger.error("TrackView::set_playing_indicator(): %s" % e)

    def update_duration(self, track_id):
        """
            Update track duration
            @param track_id as int
        """
        try:
            for disc in self.__discs:
                number = disc.number
                self._tracks_widget_left[number].update_duration(track_id)
                self._tracks_widget_right[number].update_duration(track_id)
        except Exception as e:
            Logger.error("TrackView::update_duration(): %s" % e)

    def populate(self):
        """
            Populate tracks
            @thread safe
        """
        if self._responsive_widget is None:
            if self._view_type & ViewType.DND:
                self.connect("key-press-event", self.__on_key_press_event)
            self._responsive_widget = Gtk.Grid()
            self._responsive_widget.set_column_spacing(20)
            self._responsive_widget.set_column_homogeneous(True)
            self._responsive_widget.set_property("valign", Gtk.Align.START)

            self._tracks_widget_left = {}
            self._tracks_widget_right = {}

            if self._view_type & ViewType.TWO_COLUMNS:
                self.__discs = self._album.discs
            else:
                self.__discs = [self._album.one_disc]
            self.__discs_to_load = list(self.__discs)
            for disc in self.__discs:
                self.__add_disc_container(disc.number)
        if self.__discs_to_load:
            disc = self.__discs_to_load.pop(0)
            disc_number = disc.number
            tracks = get_position_list(disc.tracks, self.__position)
            if self._view_type & ViewType.TWO_COLUMNS:
                mid_tracks = int(0.5 + len(tracks) / 2)
                widgets = {self._tracks_widget_left[disc_number]:
                           tracks[:mid_tracks],
                           self._tracks_widget_right[disc_number]:
                           tracks[mid_tracks:]}
                self.__add_tracks(OrderedDict(widgets), disc_number)
            else:
                widgets = {self._tracks_widget_left[disc_number]: tracks}
                self.__add_tracks(OrderedDict(widgets), disc_number)

    def append_rows(self, tracks):
        """
            Add track rows
            @param tracks as [Track]
        """
        widgets = {self._tracks_widget_left[0]:
                   get_position_list(tracks, len(self.children))}
        self.__add_tracks(OrderedDict(widgets), 0)

    def insert_rows(self, tracks, position):
        """
            Insert track rows
            @param tracks as [Track]
            @param position as int
        """
        widgets = {self._tracks_widget_left[0]:
                   get_position_list(tracks, position)}
        self.__add_tracks(OrderedDict(widgets), 0)

    def get_current_ordinate(self, parent):
        """
            If current track in widget, return it ordinate,
            @param parent widget as Gtk.Widget
            @return y as int
        """
        for child in self.children:
            if child.id == App().player.current_track.id:
                return child.translate_coordinates(parent, 0, 0)[1]
        return None

    def set_orientation(self, orientation):
        """
            Set columns orientation
            @param orientation as Gtk.Orientation
        """
        self.__set_orientation(orientation)

    def stop(self):
        """
            Stop loading
        """
        self.__cancellable.cancel()

    def get_populated(self):
        """
            Return True if populated
            @return bool
        """
        return self.__populated

    @property
    def children(self):
        """
            Return all rows
            @return [Gtk.ListBoxRow]
        """
        rows = []
        for disc in self.__discs:
            for widget in [
                self._tracks_widget_left[disc.number],
                self._tracks_widget_right[disc.number]
            ]:
                rows += widget.get_children()
        return rows

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        boxes = []
        for widget in self._tracks_widget_left.values():
            boxes.append(widget)
        for widget in self._tracks_widget_right.values():
            boxes.append(widget)
        return boxes

    @property
    def discs(self):
        """
            Get widget discs
            @return [Discs]
        """
        return self.__discs

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return self.get_populated()

    @property
    def requested_height(self):
        """
            Requested height: Internal tracks
            @return (minimal: int, maximal: int)
        """
        from lollypop.widgets_row_track import TrackRow
        track_height = TrackRow.get_best_height(self)
        # See Banner and row spacing
        minimal_height = maximal_height = 0
        count = len(self._album.tracks)
        mid_tracks = int(0.5 + count / 2)
        left_height = track_height * mid_tracks
        right_height = track_height * (count - mid_tracks)
        if left_height > right_height:
            minimal_height += left_height
        else:
            minimal_height += right_height
        maximal_height += left_height + right_height
        # Add height for disc label
        disc_count = len(self._album.discs)
        if disc_count > 1:
            minimal_height += track_height * disc_count
            maximal_height += track_height * disc_count
        return (minimal_height, maximal_height)

#######################
# PROTECTED           #
#######################
    def _on_adaptive_size_changed(self, widget, adaptive_size):
        """
            Change columns disposition
            @param widget as Gtk.Widget
            @param adaptive_size as AdaptiveSize
        """
        if adaptive_size & (AdaptiveSize.LARGE | AdaptiveSize.BIG):
            orientation = Gtk.Orientation.HORIZONTAL
        else:
            orientation = Gtk.Orientation.VERTICAL
        if self.__orientation != orientation:
            self.__set_orientation(orientation)

    def _on_album_updated(self, scanner, album_id):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album_id as int
        """
        if self._album.id != album_id:
            return
        removed = False
        for dic in [self._tracks_widget_left, self._tracks_widget_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    if child.track.album.id == Type.NONE:
                        removed = True
        if removed:
            for dic in [self._tracks_widget_left, self._tracks_widget_right]:
                for widget in dic.values():
                    for child in widget.get_children():
                        child.destroy()
            self.__discs = list(self.__discs)
            self.__set_duration()
            self.populate()

    def _on_tracks_populated(self, disc_number):
        """
            Tracks populated
            @param disc_number
        """
        pass

    def _on_activated(self, widget, track):
        """
            A row has been activated, play track
            @param widget as TracksWidget
            @param track as Track
        """
        tracks = []
        for child in self.children:
            tracks.append(child.track)
            child.set_state_flags(Gtk.StateFlags.NORMAL, True)
        # Do not update album list if in party or album already available
        if not App().player.is_party and\
                not App().player.track_in_playback(track):
            album = self._album.clone(True)
            album.set_tracks(tracks)
            if not App().settings.get_value("append-albums"):
                App().player.clear_albums()
            App().player.add_album(album)
            App().player.load(album.get_track(track.id))
        else:
            App().player.load(track)

#######################
# PRIVATE             #
#######################
    def __add_disc_container(self, disc_number):
        """
            Add disc container to box
            @param disc_number as int
        """
        self._tracks_widget_left[disc_number] = TracksWidget(self._view_type)
        self._tracks_widget_right[disc_number] = TracksWidget(self._view_type)
        self._tracks_widget_left[disc_number].connect("activated",
                                                      self._on_activated)
        self._tracks_widget_right[disc_number].connect("activated",
                                                       self._on_activated)

    def __set_orientation(self, orientation):
        """
            Set columns orientation
            @param orientation as Gtk.Orientation
        """
        for child in self._responsive_widget.get_children():
            self._responsive_widget.remove(child)
        idx = 0
        # Vertical
        ##########################
        #  --------Label-------- #
        #  |     Column 1      | #
        #  |     Column 2      | #
        ##########################
        # Horizontal
        ###########################
        # ---------Label--------- #
        # | Column 1 | Column 2 | #
        ###########################
        for disc in self.__discs:
            if not disc.tracks:
                continue
            show_label = len(self.__discs) > 1
            disc_names = self._album.disc_names(disc.number)
            if show_label or disc_names:
                if disc_names:
                    disc_text = ", ".join(disc_names)
                elif show_label:
                    disc_text = _("Disc %s") % disc.number
                label = Gtk.Label.new()
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.set_text(disc_text)
                label.set_property("halign", Gtk.Align.START)
                label.get_style_context().add_class("dim-label")
                label.show()
                eventbox = Gtk.EventBox()
                eventbox.connect("realize", set_cursor_hand2)
                eventbox.set_tooltip_text(_("Play"))
                eventbox.connect("button-press-event",
                                 self.__on_disc_button_press_event,
                                 disc)
                eventbox.add(label)
                eventbox.show()
                if orientation == Gtk.Orientation.VERTICAL:
                    self._responsive_widget.attach(
                        eventbox, 0, idx, 1, 1)
                else:
                    self._responsive_widget.attach(
                        eventbox, 0, idx, 2, 1)
                idx += 1
            if orientation == Gtk.Orientation.VERTICAL:
                self._responsive_widget.attach(
                          self._tracks_widget_left[disc.number],
                          0, idx, 2, 1)
                idx += 1
            else:
                self._responsive_widget.attach(
                          self._tracks_widget_left[disc.number],
                          0, idx, 1, 1)
            if self._view_type & ViewType.TWO_COLUMNS:
                if orientation == Gtk.Orientation.VERTICAL:
                    self._responsive_widget.attach(
                               self._tracks_widget_right[disc.number],
                               0, idx, 2, 1)
                else:
                    self._responsive_widget.attach(
                               self._tracks_widget_right[disc.number],
                               1, idx, 1, 1)
            idx += 1

    def __add_tracks(self, widgets, disc_number):
        """
            Add tracks for to tracks widget
            @param widgets as OrderedDict
            @param disc number as int
        """
        if self.__cancellable.is_cancelled():
            return

        widget = next(iter(widgets))
        widgets.move_to_end(widget)
        tracks = widgets[widget]

        if not tracks:
            if len(self.__discs_to_load) == 0:
                self.__populated = True
            self._on_tracks_populated(disc_number)
            self._tracks_widget_left[disc_number].show()
            self._tracks_widget_right[disc_number].show()
            return

        (track, position) = tracks.pop(0)
        if not App().settings.get_value("show-tag-tracknumber"):
            track.set_number(position + 1)
        row = TrackRow(track, self._album.artist_ids, self._view_type)
        row.show()
        widget.insert(row, position)
        GLib.idle_add(self.__add_tracks, widgets, disc_number)

    def __on_key_press_event(self, widget, event):
        """
            Handle keyboard events (DEL, ...)
            @param widget as Gtk.Widget
            @param event as Gdk.EventKey
        """
        if event.keyval == Gdk.KEY_Delete:
            for child in self.children:
                if child.get_state_flags() & Gtk.StateFlags.SELECTED:
                    pass
                    # TODO and remove signal usage

    def __on_disc_button_press_event(self, button, event, disc):
        """
            Add disc to playback
            @param button as Gtk.Button
            @param event as Gdk.ButtonEvent
            @param disc as Disc
        """
        album = Album(disc.album.id)
        album.set_tracks(disc.tracks)
        App().player.play_album(album)

    def __on_realize(self, widget, window, orientation):
        """
            Set initial orientation
            @param widget as Gtk.Widget
            @param window as AdaptiveWindow
            @param orientation as Gtk.Orientation
        """
        if orientation == Gtk.Orientation.VERTICAL:
            self.__set_orientation(orientation)
        elif window is not None:
            self._on_adaptive_size_changed(window,
                                           window.adaptive_size)
