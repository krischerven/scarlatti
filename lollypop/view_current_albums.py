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

from gi.repository import Gtk

from lollypop.utils import tracks_to_albums
from lollypop.objects_track import Track
from lollypop.view import View
from lollypop.view_albums_list import AlbumsListView
from lollypop.define import App, ViewType, MARGIN_SMALL, Size
from lollypop.helper_signals import SignalsHelper, signals
from lollypop.widgets_banner_current_albums import CurrentAlbumsBannerWidget


class CurrentAlbumsView(View, SignalsHelper):
    """
        Popover showing Albums View
    """

    @signals
    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        View.__init__(self, view_type)
        view_type |= ViewType.PLAYBACK
        view_type &= ~ViewType.SCROLLED
        self.__view = AlbumsListView([], [], view_type)
        self.__view.show()
        self.__view.set_external_scrolled(self._scrolled)
        self.__view.set_width(Size.MEDIUM)
        if view_type & ViewType.DND:
            self.__view.dnd_helper.connect("dnd-finished",
                                           self.__on_dnd_finished)
        self.__banner = CurrentAlbumsBannerWidget(self.__view)
        self.__banner.show()
        self.__overlay = Gtk.Overlay.new()
        self.__overlay.show()
        self.__overlay.add(self._scrolled)
        self._viewport.add(self.__view)
        self.__overlay.add_overlay(self.__banner)
        self.add(self.__overlay)
        return [
            (App().player, "queue-changed", "_on_queue_changed"),
            (App().player, "playback-changed", "_on_playback_changed")
        ]

    def populate(self):
        """
            Populate view
        """
        self.__view.remove_placeholder()
        if App().player.queue:
            tracks = [Track(track_id) for track_id in App().player.queue]
            albums = tracks_to_albums(tracks)
        else:
            albums = App().player.albums
        self.__view.populate(albums)

    @property
    def args(self):
        return None

#######################
# PROTECTED           #
#######################
    def _on_queue_changed(self, *ignore):
        """
            Clean view and reload if empty
        """
        queue = App().player.queue
        if queue:
            for row in self.children:
                if row.revealed:
                    for subrow in row.children:
                        if subrow.track.id not in queue:
                            subrow.destroy()
                            break
                count = len(row.album.tracks)
                for track in row.album.tracks:
                    if track.id not in queue:
                        row.album.remove_track(track)
                        if count == 1:
                            row.destroy()
                        break
        else:
            self.__view.stop()
            self.__view.clear()
            self.populate()

    def _on_playback_changed(self, *ignore):
        """
            Clear and populate view again
        """
        self.__view.stop()
        self.__view.clear()
        self.__banner.clear_button.set_sensitive(True)
        self.__banner.jump_button.set_sensitive(True)
        self.__banner.save_button.set_sensitive(True)
        self.populate()

    def _on_value_changed(self, adj):
        """
            Update banner
            @param adj as Gtk.Adjustment
        """
        View._on_value_changed(self, adj)
        reveal = self.should_reveal_header(adj)
        self.__banner.set_reveal_child(reveal)
        if reveal:
            self.__set_margin()
        else:
            self._scrolled.get_vscrollbar().set_margin_top(0)

    def _on_adaptive_changed(self, window, status):
        """
            Handle adaptive mode
            @param window as Window
            @param status as bool
        """
        View._on_adaptive_changed(self, window, status)
        self.__banner.set_view_type(self._view_type)
        self.__set_margin()

#######################
# PRIVATE             #
#######################
    def __set_margin(self):
        """
            Set margin from header
        """
        self.__view.set_margin_top(self.__banner.height + MARGIN_SMALL)
        self._scrolled.get_vscrollbar().set_margin_top(self.__banner.height)

    def __on_dnd_finished(self, dnd_helper):
        """
            Save playlist if needed
            @param dnd_helper as DNDHelper
        """
        albums = []
        for child in self.children:
            albums.append(child.album)
        App().player.set_albums(albums)
        App().player.update_next_prev()
