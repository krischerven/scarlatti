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

from gi.repository import Gtk, GObject

from lollypop.widgets_album import AlbumWidget
from lollypop.view_tracks import TracksView
from lollypop.define import App, ViewType, Sizing
from lollypop.widgets_album_banner import AlbumBannerWidget


class AlbumDetailedWidget(Gtk.Grid, AlbumWidget, TracksView):
    """
        Widget with cover and tracks
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album, genre_ids, artist_ids, view_type):
        """
            Init detailed album widget
            @param album as Album
            @param label_height as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param view_type as ViewType
        """
        Gtk.Grid.__init__(self)
        AlbumWidget.__init__(self, album, genre_ids, artist_ids)
        TracksView.__init__(self, view_type)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.__width_allocation = 0
        self.connect("size-allocate", self.__on_size_allocate)

    def populate(self):
        """
            Populate widget content
        """
        if not self.get_children():
            self.__banner = AlbumBannerWidget(self._album,
                                              self._view_type | ViewType.SMALL)
            self.__banner.show()
            TracksView.populate(self)
            self.add(self.__banner)
            self.add(self._responsive_widget)
            self._responsive_widget.show()
            self.set_selection()

    def get_current_ordinate(self, parent):
        """
            If current track in widget, return it ordinate,
            @param parent widget as Gtk.Widget
            @return y as int
        """
        for dic in [self._tracks_widget_left, self._tracks_widget_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    if child.track.id == App().player.current_track.id:
                        return child.translate_coordinates(parent, 0, 0)[1]
        return None

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        selected = self._album.id == App().player.current_track.album.id
        if selected:
            self.__banner.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self.__banner.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def set_filter_func(self, func):
        """
            Set filter function
        """
        for widget in self._tracks_widget_left.values():
            widget.set_filter_func(func)
        for widget in self._tracks_widget_right.values():
            widget.set_filter_func(func)

    @property
    def requested_height(self):
        """
            Requested height: Internal tracks or at least cover
            @return (minimal: int, maximal: int)
        """
        from lollypop.widgets_row_track import TrackRow
        track_height = TrackRow.get_best_height(self)
        minimal_height = maximal_height = track_height + 20
        count = self._album.tracks_count
        mid_tracks = int(0.5 + count / 2)
        left_height = track_height * mid_tracks
        right_height = track_height * (count - mid_tracks)
        if left_height > right_height:
            minimal_height += left_height
        else:
            minimal_height += right_height
        maximal_height += left_height + right_height
        # Add height for disc label
        if len(self._album.discs) > 1:
            minimal_height += track_height
            maximal_height += track_height
        return (minimal_height, maximal_height)

#######################
# PROTECTED           #
#######################
    def _on_tracks_populated(self, disc_number):
        """
            Emit populated signal
            @param disc_number as int
        """
        self.emit("populated")

    def _on_album_updated(self, scanner, album_id, destroy):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param destroy as bool
        """
        TracksView._on_album_updated(self, scanner, album_id, destroy)
        AlbumWidget._on_album_updated(self, scanner, album_id, destroy)

#######################
# PRIVATE             #
#######################
    def __on_size_allocate(self, widget, allocation):
        """
            Update internals
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__width_allocation == allocation.width:
            return
        self.__width_allocation = allocation.width
        (min_height, max_height) = self.requested_height
        if allocation.width < Sizing.MONSTER:
            self.set_size_request(-1, max_height)
        else:
            self.set_size_request(-1, min_height)
