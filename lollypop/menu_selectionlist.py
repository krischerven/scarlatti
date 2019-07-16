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
from hashlib import sha256

from lollypop.define import Type, App, SelectionListMask
from lollypop.shown import ShownLists, ShownPlaylists


class SelectionListMenu(Gio.Menu):
    """
        A menu for configuring SelectionList
    """

    def __init__(self, widget, rowid, mask):
        """
            Init menu
            @param widget as Gtk.Widget
            @param rowid as int
            @param mask as SelectionListMask
        """
        Gio.Menu.__init__(self)
        self.__widget = widget
        self.__rowid = rowid
        self.__mask = mask
        section = None

        if not App().devices and mask & (SelectionListMask.SIDEBAR |
                                         SelectionListMask.LIST_VIEW):
            section = Gio.Menu()
            section.append(_("No connected devices"), "app.none")
        elif mask & SelectionListMask.PLAYLISTS:
            from lollypop.menu_sync import SyncPlaylistsMenu
            section = SyncPlaylistsMenu(rowid)
        elif rowid > 0:
            from lollypop.menu_sync import SyncAlbumsMenu
            if mask & SelectionListMask.GENRES:
                section = SyncAlbumsMenu([rowid], [])
            else:
                section = SyncAlbumsMenu([], [rowid])
        elif rowid == Type.ALL or rowid == Type.ARTISTS:
            from lollypop.menu_sync import SyncAlbumsMenu
            section = SyncAlbumsMenu([], [])

        if section is not None:
            self.append_section(_("Synchronization"), section)

        # Startup menu
        if not App().settings.get_value("save-state") and\
                (rowid in [Type.POPULARS, Type.RADIOS, Type.LOVED,
                           Type.ALL, Type.RECENTS, Type.YEARS,
                           Type.RANDOMS, Type.NEVER, Type.GENRES,
                           Type.PLAYLISTS, Type.ARTISTS, Type.WEB,
                           Type.GENRES_LIST, Type.ARTISTS_LIST] or
                 mask & SelectionListMask.PLAYLISTS):
            startup_menu = Gio.Menu()
            if self.__mask & SelectionListMask.LIST_VIEW:
                exists = rowid in App().settings.get_value("startup-two-ids")
            else:
                exists = rowid in App().settings.get_value("startup-one-ids")
            action = Gio.SimpleAction.new_stateful(
                                           "default_selection_id",
                                           None,
                                           GLib.Variant.new_boolean(exists))
            App().add_action(action)
            action.connect("change-state",
                           self.__on_default_change_state,
                           rowid)
            item = Gio.MenuItem.new(_("Default on startup"),
                                    "app.default_selection_id")
            startup_menu.append_item(item)
            self.append_section(_("Startup"), startup_menu)
        # Shown menu
        if mask & (SelectionListMask.SIDEBAR |
                   SelectionListMask.LIST_VIEW) and rowid < 0:
            shown_menu = Gio.Menu()
            if mask & SelectionListMask.PLAYLISTS:
                lists = ShownPlaylists.get(True)
                wanted = App().settings.get_value("shown-playlists")
            else:
                mask |= SelectionListMask.COMPILATIONS
                lists = ShownLists.get(mask, True)
                wanted = App().settings.get_value("shown-album-lists")
            for item in lists:
                exists = item[0] in wanted
                encoded = sha256(item[1].encode("utf-8")).hexdigest()
                action = Gio.SimpleAction.new_stateful(
                    encoded,
                    None,
                    GLib.Variant.new_boolean(exists))
                action.connect("change-state",
                               self.__on_shown_change_state,
                               item[0])
                App().add_action(action)
                shown_menu.append(item[1], "app.%s" % encoded)
            # Translators: shown => items
            self.append_section(_("Sections"), shown_menu)

#######################
# PRIVATE             #
#######################
    def __on_shown_change_state(self, action, variant, rowid):
        """
            Set action value
            @param action as Gio.SimpleAction
            @param variant as GLib.Variant
            @param rowid as int
        """
        action.set_state(variant)
        if self.__mask & SelectionListMask.PLAYLISTS:
            option = "shown-playlists"
        else:
            option = "shown-album-lists"
        wanted = list(App().settings.get_value(option))
        if variant:
            wanted.append(rowid)
        else:
            wanted.remove(rowid)
        App().settings.set_value(option, GLib.Variant("ai", wanted))
        if self.__mask & SelectionListMask.PLAYLISTS:
            items = ShownPlaylists.get(True)
        else:
            items = ShownLists.get(self.__mask, True)
        if variant:
            for item in items:
                if item[0] == rowid:
                    self.__widget.add_value(item)
                    break
        else:
            self.__widget.remove_value(rowid)
            if self.__mask & SelectionListMask.SIDEBAR:
                ids = list(App().settings.get_value("startup-one-ids"))
                if rowid in ids:
                    ids.remove(rowid)
                App().settings.set_value("startup-one-ids",
                                         GLib.Variant("ai", ids))
                App().settings.set_value("startup-two-ids",
                                         GLib.Variant("ai", []))

    def __on_default_change_state(self, action, variant, rowid):
        """
            Add to playlists
            @param action as Gio.SimpleAction
            @param variant as GVariant
            @param rowid as int
        """
        if self.__mask & SelectionListMask.SIDEBAR:
            if variant:
                startup_one_ids = [rowid]
                startup_two_ids = []
            else:
                startup_one_ids = startup_two_ids = []
        elif self.__mask & SelectionListMask.LIST_VIEW:
            if variant:
                startup_one_ids = None
                startup_two_ids = [rowid]
            else:
                startup_one_ids = None
                startup_two_ids = [rowid]

        if startup_one_ids is not None:
            App().settings.set_value("startup-one-ids",
                                     GLib.Variant("ai", startup_one_ids))
        App().settings.set_value("startup-two-ids",
                                 GLib.Variant("ai", startup_two_ids))
