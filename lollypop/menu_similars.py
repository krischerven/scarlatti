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

from gettext import gettext as _

from lollypop.define import App, ArtSize, ArtBehaviour, Type
from lollypop.logger import Logger
from lollypop.utils import get_network_available, sql_escape


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


class SimilarsMenu(Gtk.Bin):
    """
        A popover with similar artists
    """

    def available():
        """
            True if menu is available
            @return bool
        """
        return get_network_available("SPOTIFY") or (
            App().lastfm is not None and get_network_available("LASTFM"))

    def __init__(self):
        """
            Init popover
        """
        Gtk.Bin.__init__(self)
        if App().settings.get_value("recent-youtube-dl"):
            path = GLib.get_user_data_dir() + "/lollypop/python/bin/youtube-dl"
            self.__show_all = GLib.file_test(path, GLib.FileTest.EXISTS)
        else:
            self.__show_all = GLib.find_program_in_path(
                "youtube-dl") is not None
        self.__added = []
        self.__artist = ""
        self.__cancellable = Gio.Cancellable()
        self.connect("unmap", self.__on_unmap)
        self.__stack = Gtk.Stack.new()
        self.__stack.show()
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__stack.set_transition_duration(200)
        self.__spinner = Gtk.Spinner.new()
        self.__spinner.show()
        self.__spinner.start()
        self.__listbox = Gtk.ListBox()
        self.__listbox.get_style_context().add_class("trackswidget")
        self.__listbox.set_vexpand(True)
        self.__listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__listbox.set_activate_on_single_click(True)
        self.__listbox.connect("row-activated", self.__on_row_activated)
        self.__listbox.show()
        self.__stack.add(self.__spinner)
        self.__stack.add(self.__listbox)
        label = Gtk.Label.new(_("No results"))
        label.get_style_context().add_class("bold")
        label.get_style_context().add_class("dim-label")
        label.show()
        self.__stack.add_named(label, "no-results")
        self.add(self.__stack)

    def populate(self, artist_id):
        """
            Populate view for artist id
            @param artist_id as int
        """
        self.__added = []
        self.__artist = App().artists.get_name(artist_id)
        providers = []
        if get_network_available("SPOTIFY"):
            providers.append(App().spotify)
        if App().lastfm is not None and get_network_available("LASTFM"):
            providers.append(App().lastfm)
        self.__populate(providers)

#######################
# PRIVATE             #
#######################
    def __populate(self, providers):
        """
            Populate view with providers
            @param providers as []
        """
        if providers:
            provider = providers.pop(0)
            App().task_helper.run(provider.get_artist_id,
                                  self.__artist, self.__cancellable,
                                  callback=(self.__on_get_artist_id,
                                            providers, provider))
        elif not self.__listbox.get_children():
            self.__stack.set_visible_child_name("no-results")
            self.__spinner.stop()

    def __on_get_artist_id(self, artist_id, providers, provider):
        """
            Get similars
            @param artist_id as str
            @param providers as []
            @param provider as SpotifyHelper/LastFM
        """
        if artist_id is None:
            if providers:
                self.__populate(providers)
            else:
                self.__stack.set_visible_child_name("no-results")
                self.__spinner.stop()
        else:
            App().task_helper.run(provider.get_similar_artists,
                                  artist_id, self.__cancellable,
                                  callback=(self.__on_similar_artists,
                                            providers))

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
        artist_name = row.artist_name
        artist_id = App().artists.get_id_for_escaped_string(
            sql_escape(artist_name))
        if artist_id is None:
            target = "web://%s" % artist_name
            App().lookup_action("search").activate(GLib.Variant("s", target))
        else:
            App().window.container.show_view([Type.ARTISTS], [artist_id])

    def __on_similar_artists(self, artists, providers):
        """
            Add artist to view
            @param artists as [str]
            @param providers as []
        """
        if artists:
            (spotify_id, artist, cover_uri) = artists.pop(0)
            if artist in self.__added:
                GLib.idle_add(self.__on_similar_artists, artists, providers)
            self.__added.append(artist)
            (artist_id, name) = App().artists.get_id(artist)
            row = None
            if artist_id is not None:
                # We want real artist name (with case)
                artist = App().artists.get_name(artist_id)
                albums = App().artists.get_albums([artist_id])
                if albums:
                    row = ArtistRow(artist, None, self.__cancellable)
            elif self.__show_all:
                row = ArtistRow(artist, cover_uri, self.__cancellable)
            if row is not None:
                row.show()
                self.__listbox.add(row)
            GLib.idle_add(self.__on_similar_artists, artists, providers)
        else:
            if self.__listbox.get_children():
                self.__stack.set_visible_child(self.__listbox)
                self.__spinner.stop()
            self.__populate(providers)
