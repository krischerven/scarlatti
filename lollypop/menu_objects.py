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

from gi.repository import Gio, Gtk, GLib

from pickle import load, dump
from gettext import gettext as _

from lollypop.define import StorageType, MARGIN_SMALL, App, CACHE_PATH
from lollypop.define import ViewType
from lollypop.menu_playlists import PlaylistsMenu
from lollypop.menu_edit import EditMenu
from lollypop.menu_playback import TrackPlaybackMenu, AlbumPlaybackMenu
from lollypop.menu_sync import SyncAlbumsMenu
from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget


class AlbumMenu(Gio.Menu):
    """
        Contextual menu for album
    """

    def __init__(self, album, view_type, header=False):
        """
            Init menu model
            @param album as Album
            @param view_type as ViewType
            @param header as bool
        """
        Gio.Menu.__init__(self)
        if header:
            from lollypop.menu_header import AlbumMenuHeader
            self.append_item(AlbumMenuHeader(album))
        if not view_type & ViewType.BANNER:
            self.append_section(_("Playback"), AlbumPlaybackMenu(album))
        from lollypop.menu_artist import ArtistAlbumsMenu
        menu = ArtistAlbumsMenu(album.artist_ids[0], view_type)
        if menu.get_n_items() != 0:
            self.append_section(_("Artist"), menu)
        section = Gio.Menu()
        if album.storage_type & (StorageType.COLLECTION | StorageType.SAVED):
            section.append_submenu(_("Playlists"), PlaylistsMenu([album]))
        if album.storage_type & StorageType.COLLECTION:
            section.append_submenu(_("Devices"), SyncAlbumsMenu([album]))
        if section.get_n_items() != 0:
            self.append_section(_("Add to"), section)
        self.append_section(_("Edit"), EditMenu(album))


class AlbumsMenu(Gio.Menu):
    """
        Contextual menu for albums
    """

    def __init__(self, albums, header=False):
        """
            Init menu model
            @param albums as [Album]
            @param header as bool
        """
        Gio.Menu.__init__(self)
        if header:
            from lollypop.menu_header import MenuHeader
            self.append_item(MenuHeader(_("Albums")))
        self.append_section(_("Devices"), SyncAlbumsMenu(albums))


class MinTrackMenu(Gio.Menu):
    """
        Contextual menu for a track
    """

    def __init__(self, track):
        """
            Init menu model
            @param track as Track
        """
        Gio.Menu.__init__(self)
        from lollypop.menu_artist import ArtistAlbumsMenu
        menu = ArtistAlbumsMenu(track.artist_ids[0], ViewType.DEFAULT)
        self.append_section(_("Artist"), menu)
        if not track.storage_type & StorageType.EPHEMERAL:
            section = Gio.Menu()
            section.append_submenu(_("Playlists"), PlaylistsMenu([track]))
            self.append_section(_("Add to"), section)
        self.append_section(_("Edit"), EditMenu(track))


class TrackMenu(Gio.Menu):
    """
        Full Contextual menu for a track
    """

    def __init__(self, track, header):
        """
            Init menu model
            @param track as Track
            @param header as bool
        """
        Gio.Menu.__init__(self)
        if header:
            from lollypop.menu_header import AlbumMenuHeader
            self.append_item(AlbumMenuHeader(track))
        self.append_section(_("Playback"), TrackPlaybackMenu(track))
        if not track.storage_type & StorageType.EPHEMERAL:
            section = Gio.Menu()
            section.append_submenu(_("Playlists"), PlaylistsMenu([track]))
            self.append_section(_("Add to"), section)
        self.append_section(_("Edit"), EditMenu(track))


class TrackMenuExt(Gtk.Grid):
    """
        Additional widgets for track menu
    """

    def __init__(self, track):
        """
            Init widget
            @param track as Track
        """
        Gtk.Grid.__init__(self)
        self.set_margin_top(MARGIN_SMALL)
        self.set_row_spacing(MARGIN_SMALL)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        if track.year is not None:
            year_label = Gtk.Label.new()
            year_label.set_text(str(track.year))
            dt = GLib.DateTime.new_from_unix_local(track.timestamp)
            year_label.set_tooltip_text(dt.format(_("%Y-%m-%d")))
            year_label.set_margin_end(5)
            year_label.get_style_context().add_class("dim-label")
            year_label.set_property("halign", Gtk.Align.START)
            year_label.set_property("hexpand", True)
            year_label.show()

        hgrid = Gtk.Grid()
        rating = RatingWidget(track)
        rating.set_property("halign", Gtk.Align.START)
        if App().window.is_adaptive:
            rating.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)
        rating.show()

        loved = LovedWidget(track)
        loved.set_property("halign", Gtk.Align.START)
        if App().window.is_adaptive:
            loved.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)
        loved.show()

        if track.year is not None:
            hgrid.add(year_label)
        hgrid.add(loved)
        hgrid.add(rating)
        hgrid.show()

        if not track.storage_type & StorageType.COLLECTION:
            try:
                escaped = GLib.uri_escape_string(track.uri, None, True)
                uri = load(open("%s/web_%s" % (CACHE_PATH, escaped), "rb"))
            except:
                uri = ""
            edit = Gtk.Entry()
            edit.set_placeholder_text(_("YouTube page address"))
            edit.set_margin_top(MARGIN_SMALL)
            edit.set_margin_start(MARGIN_SMALL)
            edit.set_margin_end(MARGIN_SMALL)
            edit.set_margin_bottom(MARGIN_SMALL)
            edit.set_property("hexpand", True)
            edit.set_text(uri)
            edit.connect("changed", self.__on_edit_changed, track)
            edit.show()
            self.add(edit)

        separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        separator.show()
        self.add(separator)
        self.add(hgrid)

#######################
# PRIVATE             #
#######################
    def __on_edit_changed(self, edit, track):
        """
            Update track uri
            @param edit as Gtk.Edit
            @param track as Track
        """
        from urllib.parse import urlparse
        uri = edit.get_text()
        parsed = urlparse(uri)
        escaped = GLib.uri_escape_string(track.uri, None, True)
        if parsed.scheme not in ["http", "https"]:
            return
        try:
            # CACHE URI
            with open("%s/web_%s" % (CACHE_PATH, escaped), "wb") as f:
                dump(uri, f)
        except:
            pass
