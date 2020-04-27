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

from lollypop.utils_album import tracks_to_albums
from lollypop.objects_track import Track
from lollypop.view import View
from lollypop.view_albums_list import AlbumsListView
from lollypop.define import App, ViewType, Size, StorageType
from lollypop.helper_signals import SignalsHelper, signals_map
from lollypop.widgets_banner_current_albums import CurrentAlbumsBannerWidget


class CurrentAlbumsView(View, SignalsHelper):
    """
        Popover showing Albums View
    """

    @signals_map
    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        View.__init__(self, StorageType.ALL,
                      view_type | ViewType.SCROLLED | ViewType.OVERLAY)
        view_type |= ViewType.PLAYBACK
        self.__view = AlbumsListView([], [], view_type)
        self.__view.show()
        self.__view.set_scrolled(self.scrolled)
        self.__view.set_width(Size.MEDIUM)
        if view_type & ViewType.DND:
            self.__view.dnd_helper.connect("dnd-finished",
                                           self.__on_dnd_finished)
        self.__banner = CurrentAlbumsBannerWidget(self.__view)
        self.__banner.show()
        self.add_widget(self.__view, self.__banner)
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
                self.__view.add_reveal_albums(albums)
            self.__view.populate(albums)
            self.show_placeholder(False)
        else:
            self.show_placeholder(True)

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {"view_type": self.view_type & ~(ViewType.ADAPTIVE |
                                                ViewType.SCROLLED |
                                                ViewType.SMALL)}

#######################
# PROTECTED           #
#######################
    def _on_queue_changed(self, *ignore):
        """
            Clean view and reload if empty
        """
        queue = App().player.queue
        if queue:
            for row in self.__view.children:
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

    def _on_playback_added(self, player, album):
        """
            Add album
            @param player as Player
            @param album as Album
        """
        self.__view.add_value(album)
        self.show_placeholder(False)

    def _on_playback_updated(self, player, album):
        """
            Reset album
            @param player as Player
            @param album as Album
        """
        for child in self.__view.children:
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
            self.__view.populate(albums)
            self.show_placeholder(False)
        else:
            self.__view.stop()
            self.__view.clear()
            self.show_placeholder(True)

    def _on_playback_removed(self, player, album):
        """
            Add album
            @param player as Player
            @param album as Album
        """
        for child in self.__view.children:
            if child.album == album:
                child.destroy()
                break
        if not self.__view_children:
            self.show_placeholder(True)

#######################
# PRIVATE             #
#######################
    def __on_dnd_finished(self, dnd_helper):
        """
            Save playlist if needed
            @param dnd_helper as DNDHelper
        """
        albums = []
        for child in self.__view.children:
            albums.append(child.album)
        App().player.set_albums(albums)
