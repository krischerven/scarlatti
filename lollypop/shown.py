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

from gettext import gettext as _

from lollypop.define import Type, App, SelectionListMask


class ShownLists:
    """
        Handle shown lists
    """

    IDS = {
        Type.POPULARS: (_("Popular albums"),
                        SelectionListMask.SIDEBAR),
        Type.RANDOMS: (_("Random albums"),
                       SelectionListMask.SIDEBAR),
        Type.LOVED: (_("Loved albums"),
                     SelectionListMask.SIDEBAR),
        Type.RECENTS: (_("Recently added albums"),
                       SelectionListMask.SIDEBAR),
        Type.NEVER: (_("Unplayed albums"),
                     SelectionListMask.SIDEBAR),
        Type.PLAYLISTS: (_("Playlists"),
                         SelectionListMask.SIDEBAR),
        Type.RADIOS: (_("Radios"),
                      SelectionListMask.SIDEBAR),
        Type.YEARS: (_("Years"),
                     SelectionListMask.SIDEBAR),
        Type.GENRES: (_("Genres"),
                      SelectionListMask.SIDEBAR),
        Type.GENRES_LIST: (_("Genres ≣"),
                           SelectionListMask.SIDEBAR),
        Type.WEB: (_("Web"),
                   SelectionListMask.SIDEBAR),
        Type.ALL: (_("Albums"),
                   SelectionListMask.SIDEBAR),
        Type.ARTISTS: (_("Artists"), SelectionListMask.SIDEBAR),
        Type.ARTISTS_LIST: (_("Artists ≣"),
                            SelectionListMask.SIDEBAR),
        Type.COMPILATIONS: (_("Compilations"), SelectionListMask.SIDEBAR),
    }

    def get(mask, get_all=False):
        """
            Get list
            @param mask as bit mask
            @param get_all as bool
            @return [(,)]
        """
        wanted = list(App().settings.get_value("shown-album-lists"))
        lists = []
        for key in ShownLists.IDS.keys():
            (string, id_mask) = ShownLists.IDS[key]
            if mask & id_mask and (get_all or key in wanted):
                lists.append((key, string, ""))
        return lists


class ShownPlaylists(ShownLists):
    """
        Handle shown playlists
    """
    IDS = {
        Type.POPULARS: _("Popular tracks"),
        Type.RANDOMS: _("Random tracks"),
        Type.LOVED: _("Loved tracks"),
        Type.RECENTS: _("Recently played"),
        Type.NEVER: _("Unplayed")
    }

    def get(get_all=False):
        """
            Get list
            @return [(,)]
        """
        wanted = App().settings.get_value("shown-playlists")
        lists = []
        for key in ShownPlaylists.IDS.keys():
            string = ShownPlaylists.IDS[key]
            if get_all or key in wanted:
                lists.append((key, string, ""))
        return lists
