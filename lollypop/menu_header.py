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

from lollypop.objects_album import Album
from lollypop.define import Type, App
from lollypop.utils import get_icon_name


class MenuHeader(Gio.MenuItem):
    """
        A menu header item
    """

    def __init__(self, type_id):
        """
            Init menu
            @param type_id as int
        """
        Gio.MenuItem.__init__(self)
        from lollypop.shown import ShownLists
        if type_id == Type.NONE:
            label = _("Sidebar")
            icon_name = "org.gnome.Lollypop-sidebar-symbolic"
        else:
            label = ShownLists.IDS[type_id]
            icon_name = get_icon_name(type_id)
        self.set_attribute_value("header", GLib.Variant("b", True))
        self.set_attribute_value("label", GLib.Variant("s", label))
        self.set_attribute_value("icon-name", GLib.Variant("s", icon_name))


class ArtistMenuHeader(Gio.MenuItem):
    """
        A menu header item for an artist
    """

    def __init__(self, artist_id):
        """
            Init menu
            @param artist_id as int
        """
        Gio.MenuItem.__init__(self)
        name = App().artists.get_name(artist_id)
        label = "<span alpha='40000'>%s</span>" % GLib.markup_escape_text(name)
        self.set_attribute_value("header", GLib.Variant("b", True))
        self.set_attribute_value("label", GLib.Variant("s", label))
        self.set_attribute_value("artist-id", GLib.Variant("i", artist_id))


class AlbumMenuHeader(Gio.MenuItem):
    """
        A menu header item for Albums/Tracks
    """

    def __init__(self, object):
        """
            Init menu
            @param object as Album/Track
        """
        Gio.MenuItem.__init__(self)
        if isinstance(object, Album):
            label = "<span alpha='40000'>%s</span>" % GLib.markup_escape_text(
                object.name)
            album_id = object.id
        else:
            label = "<b>%s</b>\n<span alpha='40000'>%s</span>" % (
                GLib.markup_escape_text(", ".join(object.artists)),
                GLib.markup_escape_text(object.name))
            album_id = object.album.id
        self.set_attribute_value("header", GLib.Variant("b", True))
        self.set_attribute_value("label", GLib.Variant("s", label))
        self.set_attribute_value("album-id", GLib.Variant("i", album_id))
