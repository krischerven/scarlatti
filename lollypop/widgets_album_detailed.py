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

from gi.repository import Gtk, GObject

from lollypop.widgets_album import AlbumWidget
from lollypop.view_tracks import TracksView
from lollypop.define import App, Sizing, ArtSize, ViewType
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
            @param genre_ids as [int]
            @param artist_ids as [int]
            @param view_type as ViewType
        """
        Gtk.Grid.__init__(self)
        AlbumWidget.__init__(self, album, genre_ids, artist_ids)
        TracksView.__init__(self, view_type)
        self.set_row_spacing(2)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.__width_allocation = 0
        self.__banner = None
        self.connect("size-allocate", self.__on_size_allocate)

    def populate(self):
        """
            Populate widget content
        """
        TracksView.populate(self)
        if not self.get_children():
            self.__banner = AlbumBannerWidget(self._album,
                                              self._view_type |
                                              ViewType.MEDIUM)
            self.__banner.show()
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
        if self.__banner is None:
            return
        selected = self._album.id == App().player.current_track.album.id
        self.__banner.set_selected(selected)

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
            Requested height: Internal tracks
            @return (minimal: int, maximal: int)
        """
        from lollypop.widgets_row_track import TrackRow
        track_height = TrackRow.get_best_height(self)
        # See Banner and row spacing
        minimal_height = maximal_height = ArtSize.BANNER + 40 + 2
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

    def _on_album_updated(self, scanner, album_id, added):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album_id as int
            @param added as bool
        """
        TracksView._on_album_updated(self, scanner, album_id)

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
        if allocation.width < Sizing.BIG:
            self.set_size_request(-1, max_height)
        else:
            self.set_size_request(-1, min_height)
