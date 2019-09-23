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


class Downloader:
    """
        Download from the web
    """

    _WEBSERVICES = [
                   ("AudioDB", "_get_audiodb_artist_artwork_uri",
                    "_get_audiodb_album_artwork_uri",
                    "_get_audiodb_artist_info"),
                   ("FanartTV", "_get_fanarttv_artist_artwork_uri",
                    None,
                    None),
                   ("Spotify", "_get_spotify_artist_artwork_uri",
                    "_get_spotify_album_artwork_uri", None),
                   ("Itunes", None,
                    "_get_itunes_album_artwork_uri", None),
                   ("Deezer", "_get_deezer_artist_artwork_uri",
                    "_get_deezer_album_artwork_uri", None),
                   ("Last.fm", None,  # Doesn't work anymore
                    "_get_lastfm_album_artwork_uri",
                    "_get_lastfm_artist_info"),
                   ("Wikipedia", None, None, None)]

    def __init__(self):
        """
            Init downloader
        """
        pass

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
