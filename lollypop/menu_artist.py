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

from gi.repository import Gio, GLib

from gettext import gettext as _

from lollypop.define import App, ViewType, Type


class ArtistMenu(Gio.Menu):
    """
        Contextual menu for artist
    """

    def __init__(self, album, view_type):
        """
            Init playlists menu
            @param album as Album
            @param view_type as ViewType
        """
        Gio.Menu.__init__(self)
        self.__album = album
        self.__set_artists_actions(view_type)

#######################
# PRIVATE             #
#######################
    def __set_artists_actions(self, view_type):
        """
            Set artist actions
            @param view_type as ViewType
        """
        if view_type & ViewType.ALBUM:
            go_artist_action = Gio.SimpleAction(name="go_artist_action")
            App().add_action(go_artist_action)
            go_artist_action.connect("activate",
                                     self.__go_to_artists)
            self.append(_("Available albums"), "app.go_artist_action")
        search_artist_action = Gio.SimpleAction(name="search_artist_action")
        App().add_action(search_artist_action)
        search_artist_action.connect("activate",
                                     self.__search_artist)
        self.append(_("Other albums"), "app.search_artist_action")

    def __search_artist(self, action, variant):
        """
            Search albums from artist
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        artist_name = App().artists.get_name(self.__album.artist_ids[0])
        target = "web://%s" % artist_name
        App().lookup_action("search").activate(GLib.Variant("s", target))

    def __go_to_artists(self, action, variant):
        """
            Show albums from artists
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_view([Type.ARTISTS],
                                         self._album.artist_ids)
