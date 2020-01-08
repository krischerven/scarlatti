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

from gi.repository import Gio, GLib

from gettext import gettext as _

from lollypop.define import App, ViewType, Type
from lollypop.utils import get_network_available, get_youtube_dl


class ArtistMenu(Gio.Menu):
    """
        Contextual menu for artist
    """
    def __init__(self, artist_id, view_type, header=False):
        """
            Init artist menu
            @param artist_id as int
            @param view_type as ViewType
            @param header as bool
        """
        Gio.Menu.__init__(self)
        if header:
            from lollypop.menu_header import ArtistMenuHeader
            self.append_item(ArtistMenuHeader(artist_id))
        if not view_type & ViewType.BANNER:
            from lollypop.menu_playback import ArtistPlaybackMenu
            self.append_section(_("Playback"), ArtistPlaybackMenu(artist_id))
        menu = ArtistAlbumsMenu(artist_id, view_type)
        if menu.get_n_items() != 0:
            self.append_section(_("Albums"), menu)


class ArtistAlbumsMenu(Gio.Menu):
    """
        Contextual menu for artist albums
    """

    def __init__(self, artist_id, view_type):
        """
            Init artist albums menu
            @param artist id as int
            @param view_type as ViewType
        """
        Gio.Menu.__init__(self)
        self.__artist_id = artist_id
        self.__set_actions(view_type)

#######################
# PRIVATE             #
#######################
    def __set_actions(self, view_type):
        """
            Set artist actions
            @param view_type as ViewType
        """
        if not view_type & ViewType.ARTIST and\
                App().artists.has_albums(self.__artist_id):
            go_artist_action = Gio.SimpleAction(name="go_artist_action")
            App().add_action(go_artist_action)
            go_artist_action.connect("activate",
                                     self.__go_to_artists)
            self.append(_("Available albums"), "app.go_artist_action")
        (path, env) = get_youtube_dl()
        if path is not None and\
                get_network_available("SPOTIFY") and\
                get_network_available("YOUTUBE"):
            search_artist_action = Gio.SimpleAction(
                name="search_artist_action")
            App().add_action(search_artist_action)
            search_artist_action.connect("activate",
                                         self.__search_artist)
            self.append(_("Albums on the Web"), "app.search_artist_action")
        if view_type & ViewType.BANNER and not view_type & ViewType.ALBUM:
            show_tracks_action = Gio.SimpleAction.new_stateful(
                "show_tracks_action",
                None,
                GLib.Variant.new_boolean(
                    App().settings.get_value("show-artist-tracks")))
            App().add_action(show_tracks_action)
            show_tracks_action.connect("change-state",
                                       self.__on_show_tracks_change_state)
            self.append(_("Show tracks"), "app.show_tracks_action")

    def __search_artist(self, action, variant):
        """
            Search albums from artist
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        artist_name = App().artists.get_name(self.__artist_id)
        App().lookup_action("search").activate(GLib.Variant("s", artist_name))

    def __go_to_artists(self, action, variant):
        """
            Show albums from artists
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_view([Type.ARTISTS],
                                         [self.__artist_id])

    def __on_show_tracks_change_state(self, action, variant):
        """
            Save option and reload view
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        action.set_state(variant)
        App().settings.set_value("show-artist-tracks", variant)
        App().window.container.reload_view()
