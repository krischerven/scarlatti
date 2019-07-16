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

from gi.repository import Gtk, GLib, Gio, Gdk

from gettext import gettext as _

from lollypop.define import App, ArtSize, ViewType, MARGIN, MARGIN_SMALL, Type
from lollypop.objects_album import Album
from lollypop.logger import Logger
from lollypop.utils import escape
from lollypop.helper_art import ArtBehaviour
from lollypop.information_store import InformationStore
from lollypop.view_albums_list import AlbumsListView
from lollypop.view import View
from lollypop.utils import on_realize


class InformationView(View):
    """
        View with artist information
    """

    def __init__(self, minimal=False):
        """
            Init artist infos
            @param follow_player as bool
        """
        View.__init__(self)
        self.__information_store = InformationStore()
        self.__information_store.connect("artist-info-changed",
                                         self.__on_artist_info_changed)
        self.__cancellable = Gio.Cancellable()
        self.__minimal = minimal
        self.__artist_name = ""
        self.__artist_id = None

    def populate(self, artist_id=None):
        """
            Show information for artists
            @param artist_id as int
        """
        self.__artist_id = artist_id
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/org/gnome/Lollypop/ArtistInformation.ui")
        builder.connect_signals(self)
        self.__scrolled = builder.get_object("scrolled")
        widget = builder.get_object("widget")
        self.add(widget)
        self.__stack = builder.get_object("stack")
        self.__artist_label = builder.get_object("artist_label")
        self.__artist_label.connect("realize", on_realize)
        title_label = builder.get_object("title_label")
        self.__artist_artwork = builder.get_object("artist_artwork")
        eventbox = builder.get_object("eventbox")
        eventbox.connect("button-release-event",
                         self.__on_label_button_release_event)
        self.__information_label = builder.get_object("bio_label")
        if artist_id is None and App().player.current_track.id is not None:
            builder.get_object("header").show()
            builder.get_object("lyrics_button").show()
            builder.get_object("lyrics_button").connect(
                "clicked",
                self.__on_lyrics_button_clicked,
                App().player.current_track)
            artist_id = App().player.current_track.album.artist_ids[0]
            title_label.set_text(App().player.current_track.title)
        self.__artist_name = App().artists.get_name(artist_id)
        if self.__minimal:
            self.__information_label.set_margin_start(MARGIN)
            self.__information_label.set_margin_end(MARGIN)
            self.__information_label.set_margin_top(MARGIN)
            self.__information_label.set_margin_bottom(MARGIN)
            self.__artist_artwork.hide()
        else:
            self.__artist_artwork.set_margin_start(MARGIN_SMALL)
            builder.get_object("header").show()
            self.__artist_label.set_text(self.__artist_name)
            self.__artist_label.show()
            title_label.show()
            App().art_helper.set_artist_artwork(
                                    self.__artist_name,
                                    ArtSize.ARTIST_SMALL * 3,
                                    ArtSize.ARTIST_SMALL * 3,
                                    self.__artist_artwork.get_scale_factor(),
                                    ArtBehaviour.ROUNDED |
                                    ArtBehaviour.CROP_SQUARE |
                                    ArtBehaviour.CACHE,
                                    self.__on_artist_artwork)
            albums_view = AlbumsListView([], [], ViewType.POPOVER)
            albums_view.set_size_request(300, -1)
            albums_view.show()
            albums_view.set_margin_start(5)
            widget.attach(albums_view, 2, 1, 1, 2)
            albums = []
            for album_id in App().albums.get_ids([artist_id], []):
                albums.append(Album(album_id))
            if not albums:
                albums = [App().player.current_track.album]
            # Allows view to be shown without lag
            GLib.idle_add(albums_view.populate, albums)
        App().task_helper.run(self.__information_store.get_information,
                              self.__artist_name,
                              callback=(self.__set_information_content, True))

#######################
# PROTECTED           #
#######################
    def _on_unmap(self, widget):
        """
            Cancel operations
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()

    def _on_label_realize(self, eventbox):
        """
            @param eventbox as Gtk.EventBox
        """
        try:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

#######################
# PRIVATE             #
#######################
    def __set_information_content(self, content, initial):
        """
            Set information
            @param content as bytes
            @param initial as bool => initial loading
        """
        if content:
            self.__information_label.set_markup(
                GLib.markup_escape_text(content.decode("utf-8")))
        elif initial:
            self.__information_label.set_text(_("Loading information"))
            self.__information_store.cache_artist_info(self.__artist_name)
        else:
            self.__information_label.set_text(
                _("No information for %s") % self.__artist_name)

    def __get_artist_artwork_path_from_cache(self, artist, size):
        """
            Get artist artwork path
            @param artist as str
            @param size as int
            @return str
        """
        path = InformationStore.get_artwork_path(
            artist, size, self.get_scale_factor())
        if path is not None:
            return path
        return None

    def __on_lyrics_button_clicked(self, button, track):
        """
            Show lyrics
            @param button as Gtk.Button
            @param track as Track
        """
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.popdown()
        App().window.container.show_lyrics(track)

    def _on_artist_button_release_event(self, eventbox, event):
        """
            Go to artist view
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        popover = self.get_ancestor(Gtk.Popover)
        if popover is not None:
            popover.popdown()
        if App().player.current_track.id is None:
            return
        GLib.idle_add(App().window.container.show_view,
                      [Type.ARTISTS],
                      App().player.current_track.album.artist_ids)

    def __on_label_button_release_event(self, button, event):
        """
            Show information cache (for edition)
            @param button as Gtk.Button
            @param event as Gdk.Event
        """
        uri = "file://%s/%s.txt" % (App().art._INFO_PATH,
                                    escape(self.__artist_name))
        f = Gio.File.new_for_uri(uri)
        if not f.query_exists():
            f.replace_contents(b"", None, False,
                               Gio.FileCreateFlags.NONE, None)
        Gtk.show_uri_on_window(App().window,
                               uri,
                               Gdk.CURRENT_TIME)

    def __on_artist_artwork(self, surface):
        """
            Finish widget initialisation
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__artist_artwork.hide()
        else:
            self.__artist_artwork.set_from_surface(surface)

    def __on_artist_info_changed(self, information_store, artist):
        """
            Update information
            @param information_store as InformationStore
            @param artist as str
        """
        if artist == self.__artist_name:
            App().task_helper.run(self.__information_store.get_information,
                                  self.__artist_name,
                                  callback=(self.__set_information_content,
                                            False))
