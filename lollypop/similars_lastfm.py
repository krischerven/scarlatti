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

from lollypop.define import LASTFM_API_KEY, LASTFM_API_SECRET
from lollypop.logger import Logger
from pylast import LastFMNetwork


class LastFMSimilars:
    """
        Search similar artists with Last.FM
    """
    def __init__(self):
        """
            Init provider
        """
        self.__pylast = LastFMNetwork(api_key=LASTFM_API_KEY,
                                      api_secret=LASTFM_API_SECRET)

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
        return result
