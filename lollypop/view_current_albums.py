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

from gi.repository import GLib

from lollypop.utils_album import tracks_to_albums
from lollypop.utils import emit_signal
from lollypop.objects_track import Track
from lollypop.view_albums_list import AlbumsListView
from lollypop.define import App, ViewType, Size, MARGIN
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.widgets_banner_current_albums import CurrentAlbumsBannerWidget


class CurrentAlbumsView(AlbumsListView, SignalsHelper):
    """
        Popover showing Albums View
    """

    @signals_map
    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        AlbumsListView.__init__(self, [], [],
                                view_type |
                                ViewType.SCROLLED |
                                ViewType.OVERLAY |
                                ViewType.PLAYBACK)
        self.box.set_width(Size.MEDIUM)
        if view_type & ViewType.DND:
            self.dnd_helper.connect("dnd-finished", self.__on_dnd_finished)
        self.__banner = CurrentAlbumsBannerWidget(self, view_type)
        self.__banner.show()
        self.add_widget(self.box, self.__banner)
        self.allow_duplicate("_on_queue_changed")
        self.allow_duplicate("_on_playback_added")
        self.allow_duplicate("_on_playback_updated")
        self.allow_duplicate("_on_playback_removed")
        return [
            (App().player, "queue-changed", "_on_queue_changed"),
            (App().player, "playback-added", "_on_playback_added"),
            (App().player, "playback-setted", "_on_playback_setted"),
            (App().player, "playback-updated", "_on_playback_updated"),
            (App().player, "playback-removed", "_on_playback_removed")
        ]

    def populate(self):
        """
            Populate view
        """
        if App().player.queue:
            tracks = [Track(track_id) for track_id in App().player.queue]
            albums = tracks_to_albums(tracks)
        else:
            albums = App().player.albums
        if albums:
            if len(albums) == 1:
                self.add_reveal_albums(albums)
            AlbumsListView.populate(self, albums)
            self.show_placeholder(False)
        else:
            self.show_placeholder(True)

    def clear(self):
        """
            Clear the view
        """
        if not App().player.radio_cancellable.is_cancelled():
            App().player.radio_cancellable.cancel()
            GLib.timeout_add(500, self.clear)
        else:
            AlbumsListView.clear(self)
            App().player.clear_albums()

    @property
    def filtered(self):
        """
            Get filtered children
            @return [Gtk.Widget]
        """
        filtered = []
        for child in self.children:
            filtered.append(child)
            for subchild in child.children:
                filtered.append(subchild)
        return filtered

    @property
    def scroll_shift(self):
        """
            Get scroll shift for y axes
            @return int
        """
        return self.__banner.height + MARGIN

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
            self.stop()
            AlbumsListView.clear(self)
            self.populate()

    def _on_playback_added(self, player, album):
        """
            Add album
            @param player as Player
            @param album as Album
        """
        self.add_value(album)
        self.show_placeholder(False)

    def _on_playback_updated(self, player, album):
        """
            Reset album
            @param player as Player
            @param album as Album
        """
        for child in self.children:
            if child.album == album:
                child.reset()
                break

    def _on_playback_setted(self, player, albums):
        """
            Add album
            @param player as Player
            @param albums as [Album]
        """
        if albums:
            self.stop()
            AlbumsListView.clear(self)
            AlbumsListView.populate(self, albums)
            self.show_placeholder(False)
        else:
            self.stop()
            AlbumsListView.clear(self)
            self.show_placeholder(True)

    def _on_playback_removed(self, player, album):
        """
            Add album
            @param player as Player
            @param album as Album
        """
        for child in self.children:
            if child.album == album:
                child.destroy()
                break
        if not self.children:
            self.show_placeholder(True)

    def _on_row_activated(self, row, track):
        """
            Start playback
            @param row as AlbumRow
            @param track_id as int
        """
        App().player.load(track)

    def _on_row_destroy(self, row):
        """
            Remove album from playback
            @param row as AlbumRow
        """
        if row.album.id in App().player.album_ids:
            if App().player.current_track in row.album.tracks:
                App().player.skip_album()
            App().player.remove_album(row.album)
        else:
            App().player.add_album(row.album)

    def _on_track_removed(self, row, track):
        """
            Remove track from playback
            @param row as AlbumRow
            @param track as Track
        """
        if App().player.current_track == track:
            if App().player.next_track.id != track.id:
                App().player.next()
        row.album.remove_track(track)
        emit_signal(App().player, "playback-updated", row.album)
        if not row.children:
            row.destroy()

#######################
# PRIVATE             #
#######################
    def __on_dnd_finished(self, dnd_helper):
        """
            Save playlist if needed
            @param dnd_helper as DNDHelper
        """
        albums = []
        for child in self.children:
            albums.append(child.album)
        App().player.set_albums(albums, False)
