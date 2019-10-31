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

from gi.repository import GLib, Gtk, Gdk, Gio, Pango, GObject

from gettext import gettext as _

from lollypop.widgets_tracks import TracksWidget
from lollypop.widgets_row_track import TrackRow
from lollypop.objects_album import Album
from lollypop.logger import Logger
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.utils import set_cursor_type, emit_signal
from lollypop.define import App, Type, ViewType, IndicatorType
from lollypop.define import Size
from lollypop.helper_size_allocation import SizeAllocationHelper


class TracksView(Gtk.Bin, SignalsHelper, SizeAllocationHelper):
    """
        Responsive view showing discs on one or two rows
    """

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST,
                      None, (GObject.TYPE_PYOBJECT,)),
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "track-removed": (GObject.SignalFlags.RUN_FIRST, None,
                          (GObject.TYPE_PYOBJECT,)),
    }

    @signals_map
    def __init__(self, album, view_type):
        """
            Init view
            @param album as Album
            @param view_type as ViewType
        """
        Gtk.Bin.__init__(self)
        self.__view_type = view_type
        self.__album = album
        self._tracks_widget_left = {}
        self._tracks_widget_right = {}
        self.__discs = []
        self.__discs_to_load = []
        self.__responsive_widget = None
        self.__orientation = None
        self.__populated = False
        self.__cancellable = Gio.Cancellable()
        self.__show_tag_tracknumber = App().settings.get_value(
            "show-tag-tracknumber")
        self.connect("realize", self.__on_realize)
        return [
            (App().player, "loading-changed", "_on_loading_changed")
        ]

    def populate(self):
        """
            Populate tracks lazy
        """
        def load_disc(items, disc_number, position=0):
            if items:
                (widget, tracks) = items.pop(0)
                self.__add_tracks(widget, tracks, position)
                position += len(tracks)
                widget.show()
                GLib.idle_add(load_disc, items, disc_number, position)
            else:
                emit_signal(self, "populated")

        self.__init()
        if self.__discs_to_load:
            disc = self.__discs_to_load.pop(0)
            disc_number = disc.number
            tracks = disc.tracks
            items = []
            if self.__view_type & ViewType.SINGLE_COLUMN:
                items.append((self._tracks_widget_left[0], tracks))
            else:
                mid_tracks = int(0.5 + len(tracks) / 2)
                items.append((self._tracks_widget_left[disc_number],
                              tracks[:mid_tracks]))
                items.append((self._tracks_widget_right[disc_number],
                              tracks[mid_tracks:]))
            load_disc(items, disc_number)
        else:
            self.__populated = True
            emit_signal(self, "populated")
            if not self.children:
                text = (_("""This album has no track."""
                          """ Check tags, all 'album artist'"""
                          """ tags should be in 'artist' tags"""))
                label = Gtk.Label.new(text)
                label.get_style_context().add_class("text-large")
                label.show()
                self.__responsive_widget.insert_row(0)
                self.__responsive_widget.attach(label, 0, 0, 2, 1)

    def append_row(self, track):
        """
            Append a track
            ONE COLUMN ONLY
            @param track as Track
            @param position as int
        """
        self.__init()
        self.__album.append_track(track)
        for key in self._tracks_widget_left.keys():
            self.__add_tracks(self._tracks_widget_left[key], [track])
            return

    def append_rows(self, tracks):
        """
            Add track rows
            ONE COLUMN ONLY
            @param tracks as [Track]
        """
        self.__init()
        self.__album.append_tracks(tracks)
        for key in self._tracks_widget_left.keys():
            self.__add_tracks(self._tracks_widget_left[key], tracks)
            return

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

    def stop(self):
        """
            Stop loading
        """
        self.__cancellable.cancel()

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
        return self.__populated

#######################
# PROTECTED           #
#######################
    def _handle_width_allocate(self, allocation):
        """
            Change columns disposition
            @param allocation as Gtk.Allocation
        """
        if SizeAllocationHelper._handle_width_allocate(self, allocation):
            if allocation.width >= Size.NORMAL:
                orientation = Gtk.Orientation.HORIZONTAL
            else:
                orientation = Gtk.Orientation.VERTICAL
            if self.__orientation != orientation:
                self.__set_orientation(orientation)

    def _on_loading_changed(self, player, status, track):
        """
            Update row loading status
            @param player as Player
            @param status as bool
            @param track as Track
        """
        if not self.__album.is_web:
            return
        for row in self.children:
            if row.track.id == track.id:
                row.set_indicator(IndicatorType.LOADING)
            else:
                row.set_indicator()

    def _on_album_updated(self, scanner, album_id):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album_id as int
        """
        if self.__album.id != album_id:
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

    def _on_activated(self, widget, track):
        """
            Handle playback if album or pass signal
            @param widget as TracksWidget
            @param track as Track
        """
        if self.__view_type & ViewType.ALBUM:
            tracks = []
            for child in self.children:
                tracks.append(child.track)
                child.set_state_flags(Gtk.StateFlags.NORMAL, True)
            # Do not update album list if in party or album already available
            if not App().player.is_party and\
                    not App().player.track_in_playback(track):
                album = Album(track.album.id)
                album.set_tracks(tracks)
                if not App().settings.get_value("append-albums"):
                    App().player.clear_albums()
                App().player.add_album(album)
                App().player.load(album.get_track(track.id))
            else:
                App().player.load(track)
        else:
            emit_signal(self, "activated", track)

#######################
# PRIVATE             #
#######################
    def __init(self):
        """
            Init main widget
        """
        if self.__responsive_widget is None:
            if self.__view_type & ViewType.DND:
                self.connect("key-press-event", self.__on_key_press_event)
            self.__responsive_widget = Gtk.Grid()
            self.__responsive_widget.set_column_spacing(20)
            self.__responsive_widget.set_column_homogeneous(True)
            self.__responsive_widget.set_property("valign", Gtk.Align.START)
            if self.__view_type & ViewType.SINGLE_COLUMN:
                self.__discs = [self.__album.one_disc]
            else:
                self.__discs = self.__album.discs
            for disc in self.__discs:
                self.__add_disc_container(disc.number)
            self.add(self.__responsive_widget)
            self.__responsive_widget.show()
            self.__discs_to_load = list(self.__discs)

    def __add_disc_container(self, disc_number):
        """
            Add disc container to box
            @param disc_number as int
        """
        self._tracks_widget_left[disc_number] = TracksWidget(self.__view_type)
        self._tracks_widget_right[disc_number] = TracksWidget(self.__view_type)
        self._tracks_widget_left[disc_number].connect("activated",
                                                      self._on_activated)
        self._tracks_widget_right[disc_number].connect("activated",
                                                       self._on_activated)

    def __set_orientation(self, orientation):
        """
            Set columns orientation
            @param orientation as Gtk.Orientation
        """
        if self.__orientation == orientation:
            return
        self.__orientation = orientation
        for child in self.__responsive_widget.get_children():
            self.__responsive_widget.remove(child)
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
            show_label = len(self.__discs) > 1
            disc_names = self.__album.disc_names(disc.number)
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
                eventbox.connect("realize", set_cursor_type)
                eventbox.set_tooltip_text(_("Play"))
                eventbox.connect("button-press-event",
                                 self.__on_disc_button_press_event,
                                 disc)
                eventbox.add(label)
                eventbox.show()
                if orientation == Gtk.Orientation.VERTICAL:
                    self.__responsive_widget.attach(
                        eventbox, 0, idx, 1, 1)
                else:
                    self.__responsive_widget.attach(
                        eventbox, 0, idx, 2, 1)
                idx += 1
            if orientation == Gtk.Orientation.VERTICAL:
                self.__responsive_widget.attach(
                          self._tracks_widget_left[disc.number],
                          0, idx, 2, 1)
                idx += 1
            else:
                self.__responsive_widget.attach(
                          self._tracks_widget_left[disc.number],
                          0, idx, 1, 1)
            if not self.__view_type & ViewType.SINGLE_COLUMN:
                if orientation == Gtk.Orientation.VERTICAL:
                    self.__responsive_widget.attach(
                               self._tracks_widget_right[disc.number],
                               0, idx, 2, 1)
                else:
                    self.__responsive_widget.attach(
                               self._tracks_widget_right[disc.number],
                               1, idx, 1, 1)
            idx += 1

    def __add_tracks(self, widget, tracks, position=0):
        """
            Add tracks to widget
            @param widget as Gtk.ListBox
            @param tracks as [Track]
        """
        for track in tracks:
            if not self.__show_tag_tracknumber and\
                    self.__view_type & ViewType.ALBUM:
                track.set_number(position + 1)
            row = TrackRow(track, self.__album.artist_ids, self.__view_type)
            row.show()
            row.connect("removed", self.__on_track_row_removed)
            widget.add(row)
            position += 1

    def __on_track_row_removed(self, row):
        """
            Pass signal
            @param row as TrackRow
        """
        emit_signal(self, "track-removed", row)

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

    def __on_realize(self, widget):
        """
            Set initial orientation
            @param widget as Gtk.Widget
            @param window as AdaptiveWindow
            @param orientation as Gtk.Orientation
        """
        if self.__view_type & ViewType.SINGLE_COLUMN or\
                App().settings.get_value("force-single-column"):
            self.__set_orientation(Gtk.Orientation.VERTICAL)
        elif self.__view_type & ViewType.TWO_COLUMNS:
            self.__set_orientation(Gtk.Orientation.HORIZONTAL)
        else:
            # We need to listen to parent allocation as currently, we have
            # no children
            SizeAllocationHelper.__init__(self, True)
