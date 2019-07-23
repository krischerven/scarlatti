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

from gi.repository import Gtk, Gio, GLib, Pango

from lollypop.define import App, ArtSize, ArtBehaviour
from lollypop.widgets_utils import Popover
from lollypop.logger import Logger
from lollypop.utils import get_network_available
from lollypop.helper_signals import SignalsHelper, signals_map


class ArtistRow(Gtk.ListBoxRow):
    """
        An artist row
    """

    def __init__(self, artist_name, cover_uri, cancellable):
        """
            Init row
            @param artist_name as str
            @param cover_uri as str
            @param cancellable as Gio.Cancellable
        """
        Gtk.ListBoxRow.__init__(self)
        self.__artist_name = artist_name
        self.__cover_uri = cover_uri
        self.__cancellable = cancellable
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        label = Gtk.Label.new(artist_name)
        label.set_property("halign", Gtk.Align.START)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__artwork = Gtk.Image.new()
        self.__artwork.set_size_request(ArtSize.SMALL,
                                        ArtSize.SMALL)
        App().art_helper.set_artist_artwork(artist_name,
                                            ArtSize.SMALL,
                                            ArtSize.SMALL,
                                            self.get_scale_factor(),
                                            ArtBehaviour.CROP |
                                            ArtBehaviour.CACHE |
                                            ArtBehaviour.ROUNDED,
                                            self.__on_artist_artwork)
        grid.add(self.__artwork)
        grid.add(label)
        grid.show_all()
        self.add(grid)

    @property
    def artist_name(self):
        """
            Get artist name
            @return str
        """
        return self.__artist_name

#######################
# PRIVATE             #
#######################
    def __on_uri_content(self, uri, status, data):
        """
            Save artwork to cache and set artist artwork
            @param uri as str
            @param status as bool
            @param data as bytes
        """
        try:
            if not status:
                return
            self.__cover_data = data
            scale_factor = self.get_scale_factor()
            App().art.add_artist_artwork(self.__artist_name, data, True)
            App().art_helper.set_artist_artwork(self.__artist_name,
                                                ArtSize.SMALL,
                                                ArtSize.SMALL,
                                                scale_factor,
                                                ArtBehaviour.CROP |
                                                ArtBehaviour.CACHE |
                                                ArtBehaviour.ROUNDED,
                                                self.__on_artist_artwork)
        except Exception as e:
            Logger.error("ArtistRow::__on_uri_content(): %s", e)

    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as cairo.Surface
        """
        if surface is None:
            # Last chance to get a cover
            if self.__cover_uri is not None:
                App().task_helper.load_uri_content(self.__cover_uri,
                                                   self.__cancellable,
                                                   self.__on_uri_content)
                self.__cover_uri = None
            self.__artwork.get_style_context().add_class("artwork-icon")
            self.__artwork.set_from_icon_name("avatar-default-symbolic",
                                              Gtk.IconSize.INVALID)
            # artwork-icon padding is 5px
            self.__artwork.set_pixel_size(ArtSize.SMALL - 20)
        else:
            self.__artwork.get_style_context().remove_class("artwork-icon")
            self.__artwork.set_from_surface(surface)


class SimilarsPopover(Popover, SignalsHelper):
    """
        A popover with similar artists
    """

    @signals_map
    def __init__(self):
        """
            Init popover
        """
        Popover.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SimilarsPopover.ui")
        self.__show_all = GLib.find_program_in_path("youtube-dl") is not None
        self.__added = []
        self.__cancellable = Gio.Cancellable()
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)
        self.__stack = builder.get_object("stack")
        self.__spinner = builder.get_object("spinner")
        self.__spinner.start()
        self.__listbox = Gtk.ListBox()
        self.__listbox.get_style_context().add_class("trackswidget")
        self.__listbox.set_vexpand(True)
        self.__listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__listbox.set_activate_on_single_click(True)
        self.__listbox.connect("row-activated", self.__on_row_activated)
        self.__listbox.show()
        self.__stack.add(self.__listbox)
        self.add(builder.get_object("widget"))
        return [
            (App().lastfm, "new-artist", "_on_new_artist"),
            (App().spotify, "new-artist", "_on_new_artist")
        ]

    def populate(self, artist_ids):
        """
            Populate view artist ids
            @param artist_ids as int
        """
        self.__providers = 1
        artists = []
        for artist_id in artist_ids:
            artist_name = App().artists.get_name(artist_id)
            artists.append(artist_name)
            if get_network_available("SPOTIFY"):
                App().spotify.get_artist_id(artist_name,
                                            self.__on_get_artist_id)
        if App().lastfm is not None and get_network_available("LASTFM"):
            self.__providers = 2
            App().task_helper.run(self.__search_lastfm_similars, artists)

#######################
# PROTECTED           #
#######################
    def _on_new_artist(self, provider, artist, cover_uri):
        """
            Add artist to view
            @param provider as Spotify/LastFM
            @param artist as str
        """
        if artist is None:
            self.__providers -= 1
            if self.__providers == 0:
                self.__stack.set_visible_child_name("no-result")
                self.__spinner.stop()
            return
        if artist in self.__added:
            return
        self.__added.append(artist)
        artist_id = App().artists.get_id(artist)
        row = None
        if artist_id is not None:
            # We want real artist name (with case)
            artist_name = App().artists.get_name(artist_id)
            albums = App().artists.get_albums([artist_id])
            if albums:
                row = ArtistRow(artist_name, None, self.__cancellable)
        elif self.__show_all:
            row = ArtistRow(artist, cover_uri, self.__cancellable)
        if row is not None:
            row.show()
            self.__listbox.add(row)
        self.__stack.set_visible_child(self.__listbox)

#######################
# PRIVATE             #
#######################
    def __search_lastfm_similars(self, artists):
        """
            Search similars artists from lastfm
            @param artists as [str]
            @param scale_factor as int
        """
        for artist in artists:
            if not self.__cancellable.is_cancelled():
                App().lastfm.search_similar_artists(artist,
                                                    self.__cancellable)

    def __on_get_artist_id(self, artist_id):
        """
            Get similars
            @param artist_id as str
        """
        if artist_id is None:
            self.__stack.set_visible_child_name("no-result")
            self.__spinner.stop()
            return
        App().task_helper.run(App().spotify.search_similar_artists, artist_id,
                              self.__cancellable)

    def __on_map(self, widget):
        """
            Resize widget on map
            @param widget as Gtk.Widget
        """
        self.set_size_request(300, 400)

    def __on_unmap(self, widget):
        """
            Cancel loading
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()

    def __on_row_activated(self, widget, row):
        """
            Play searched item when selected
            @param widget as Gtk.ListBox
            @param row as Gtk.ListBoxRow
        """
        self.popdown()
        artist_name = row.artist_name
        artist_id = App().artists.get_id(artist_name)
        if artist_id is None:
            target = "web://%s" % artist_name
        else:
            target = "local://%s" % artist_name
        App().lookup_action("search").activate(GLib.Variant("s", target))
