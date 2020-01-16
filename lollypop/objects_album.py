# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2015 Jean-Philippe Braun <eon@patapon.info>
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

from lollypop.define import App, StorageType, ScanUpdate
from lollypop.objects_track import Track
from lollypop.objects import Base
from lollypop.utils import emit_signal


class Disc:
    """
        Represent an album disc
    """

    def __init__(self, album, disc_number, disallow_ignored_tracks):
        self.db = App().albums
        self.__tracks = []
        self.__album = album
        self.__number = disc_number
        self.__disallow_ignored_tracks = disallow_ignored_tracks

    def __del__(self):
        """
            Remove ref cycles
        """
        self.__album = None

    def set_tracks(self, tracks):
        """
            Set disc tracks
            @param tracks as [Track]
        """
        self.__tracks = tracks

    @property
    def number(self):
        """
            Get disc number
        """
        return self.__number

    @property
    def album(self):
        """
            Get disc album
            @return Album
        """
        return self.__album

    @property
    def track_ids(self):
        """
            Get disc track ids
            @return [int]
        """
        return [track.id for track in self.tracks]

    @property
    def track_uris(self):
        """
            Get disc track uris
            @return [str]
        """
        return [track.uri for track in self.tracks]

    @property
    def tracks(self):
        """
            Get disc tracks
            @return [Track]
        """
        if not self.__tracks and self.album.id is not None:
            self.__tracks = [Track(track_id, self.album)
                             for track_id in self.db.get_disc_track_ids(
                self.album.id,
                self.album.genre_ids,
                self.album.artist_ids,
                self.number,
                self.__disallow_ignored_tracks)]
        return self.__tracks


class Album(Base):
    """
        Represent an album
    """
    DEFAULTS = {"name": "",
                "artists": [],
                "artist_ids": [],
                "year": None,
                "timestamp": 0,
                "uri": "",
                "duration": 0,
                "popularity": 0,
                "mtime": 1,
                "synced": 0,
                "loved": False,
                "storage_type": 0,
                "mb_album_id": None}

    def __init__(self, album_id=None, genre_ids=[], artist_ids=[],
                 disallow_ignored_tracks=False):
        """
            Init album
            @param album_id as int
            @param genre_ids as [int]
            @param disallow_ignored_tracks as bool
        """
        Base.__init__(self, App().albums)
        self.id = album_id
        self.genre_ids = genre_ids
        self._tracks = []
        self._discs = []
        self.__disallow_ignored_tracks = disallow_ignored_tracks
        self.__one_disc = None
        # Use artist ids from db else
        if artist_ids:
            self.artist_ids = artist_ids

    def set_discs(self, discs):
        """
            Set album discs
            @param discs as [Disc]
        """
        self._discs = discs

    def set_tracks(self, tracks, clone=True):
        """
            Set album tracks
            @param tracks as [Track]
            @param clone as bool
        """
        if clone:
            self._tracks = []
            for track in tracks:
                new_track = Track(track.id, self)
                self._tracks.append(new_track)
        else:
            self._tracks = tracks

    def append_track(self, track, clone=True):
        """
            Append track to album
            @param track as Track
            @param clone as bool
        """
        if clone:
            self._tracks.append(Track(track.id, self))
        else:
            self._tracks.append(track)
            track.set_album(self)

    def append_tracks(self, tracks, clone=True):
        """
            Append tracks to album
            @param tracks as [Track]
            @param clone as bool
        """
        for track in tracks:
            self.append_track(track, clone)

    def remove_track(self, track):
        """
            Remove track from album
            @param track as Track
            @return True if album empty
        """
        for _track in self.tracks:
            if track.id == _track.id:
                self._tracks.remove(_track)
        return len(self._tracks) == 0

    def reset_tracks(self):
        """
            Reset album tracks
        """
        self._tracks = []
        self._discs = []

    def disc_names(self, disc):
        """
            Disc names
            @param disc as int
            @return disc names as [str]
        """
        return self.db.get_disc_names(self.id, disc)

    def set_loved(self, loved):
        """
            Mark album as loved
            @param loved as bool
        """
        if self.id >= 0:
            self.db.set_loved(self.id, loved)
            self.loved = loved

    def set_uri(self, uri):
        """
            Set album uri
            @param uri as str
        """
        if self.id >= 0:
            self.db.set_uri(self.id, uri)
        self.uri = uri

    def get_track(self, track_id):
        """
            Get track
            @param track_id as int
            @return Track
        """
        for track in self.tracks:
            if track.id == track_id:
                return track
        return Track()

    def save(self, save):
        """
            Save album to collection
            @param save as bool
        """
        if save:
            self.db.set_storage_type(self.id, StorageType.SAVED)
        else:
            self.db.set_storage_type(self.id, StorageType.EPHEMERAL)
        for track in self.tracks:
            track.save(save)
        self.reset("mtime")
        if save:
            for artist_id in self.artist_ids:
                emit_signal(App().scanner, "artist-updated",
                            artist_id, ScanUpdate.ADDED)
            emit_signal(App().scanner, "album-updated", self.id,
                        ScanUpdate.ADDED)
        else:
            for artist_id in self.artist_ids:
                emit_signal(App().scanner, "artist-updated", artist_id,
                            ScanUpdate.REMOVED)
            emit_signal(App().scanner, "album-updated", self.id,
                        ScanUpdate.REMOVED)

    def set_synced(self, mask):
        """
            Set synced mask
            @param mask as int
        """
        self.db.set_synced(self.id, mask)
        self.synced = mask

    @property
    def is_web(self):
        """
            True if track is a web track
            @return bool
        """
        return not self.storage_type & (StorageType.COLLECTION |
                                        StorageType.EXTERNAL)

    @property
    def tracks_count(self):
        """
            Get tracks count
            @return int
        """
        if self._tracks:
            return len(self._tracks)
        else:
            return self.db.get_tracks_count(
                self.id,
                self.genre_ids,
                self.artist_ids)

    @property
    def track_ids(self):
        """
            Get album track ids
            @return [int]
        """
        return [track.id for track in self.tracks]

    @property
    def track_uris(self):
        """
            Get album track uris
            @return [str]
        """
        return [track.uri for track in self.tracks]

    @property
    def tracks(self):
        """
            Get album tracks
            @return [Track]
        """
        if not self._tracks and self.id is not None:
            for disc in self.discs:
                self._tracks += disc.tracks
        return self._tracks

    @property
    def one_disc(self):
        """
            Get album as one disc
            @return Disc
        """
        if self.__one_disc is None:
            tracks = self.tracks
            self.__one_disc = Disc(self, 0, self.__disallow_ignored_tracks)
            self.__one_disc.set_tracks(tracks)
        return self.__one_disc

    @property
    def discs(self):
        """
            Get albums discs
            @return [Disc]
        """
        if not self._discs:
            disc_numbers = self.db.get_discs(self.id)
            for disc_number in disc_numbers:
                disc = Disc(self, disc_number, self.__disallow_ignored_tracks)
                if disc.tracks:
                    self._discs.append(disc)
        return self._discs
