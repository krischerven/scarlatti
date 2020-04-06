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

from pylast import LastFMNetwork
from random import choice, shuffle

from lollypop.define import LASTFM_API_KEY, LASTFM_API_SECRET, App
from lollypop.logger import Logger
from lollypop.utils import emit_signal
from lollypop.helper_web_musicbrainz import MusicBrainzWebHelper


# Last.FM API is not useful to get albums
class LastFMSimilars(MusicBrainzWebHelper):
    """
        Search similar artists with Last.FM
    """
    def __init__(self):
        """
            Init provider
        """
        MusicBrainzWebHelper.__init__(self)
        self.__pylast = LastFMNetwork(api_key=LASTFM_API_KEY,
                                      api_secret=LASTFM_API_SECRET)

    def load_similars(self, artist_ids, storage_type, cancellable):
        """
            Load similar artists for artist ids
            @param artist_ids as int
            @param storage_type as StorageType
            @param cancellable as Gio.Cancellable
        """
        names = [App().artists.get_name(artist_id) for artist_id in artist_ids]
        result = self.get_similar_artists(names, cancellable)
        artist_ids = []
        for (artist_name, cover_uri) in result:
            artist_id = self.get_artist_id(artist_name, cancellable)
            if artist_id is not None:
                artist_ids.append(artist_id)
        track_ids = []
        for artist_id in artist_ids:
            _track_ids = self.get_artist_top_tracks(artist_id, cancellable)
            if not _track_ids:
                continue
            # We want some randomizing so keep tracks for later usage
            track_id = choice(_track_ids)
            track_ids += _track_ids
            payload = self.get_track_payload(track_id)
            self.save_tracks_payload_to_db([payload],
                                           storage_type,
                                           True,
                                           cancellable)
        shuffle(track_ids)
        for track_id in track_ids:
            payload = self.get_track_payload(track_id)
            self.save_tracks_payload_to_db([payload],
                                           storage_type,
                                           True,
                                           cancellable)
        emit_signal(self, "finished")

    def get_similar_artists(self, artist_names, cancellable):
        """
            Search similar artists
            @param artist_names as [str]
            @param cancellable as Gio.Cancellable
            @return [(str, str)] as [(artist_name, cover_uri)]
        """
        result = []
        for artist_name in artist_names:
            try:
                artist_item = self.__pylast.get_artist(artist_name)
                for similar_item in artist_item.get_similar(10):
                    if cancellable.is_cancelled():
                        raise Exception("cancelled")
                    result.append((similar_item.item.name,
                                   similar_item.item.get_cover_image()))
            except Exception as e:
                Logger.error("LastFMSimilars::get_similar_artists(): %s", e)
        if result:
            Logger.info("Found similar artists with LastFMSimilars")
        return result
