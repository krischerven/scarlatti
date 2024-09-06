# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

import os
import shutil

from gi.repository import Gio, GLib

from gettext import gettext as _
from hashlib import sha256

from scarlatti.define import Type, App, SelectionListMask, ARTIST_WIKI_PATH
from scarlatti.shown import ShownLists, ShownPlaylists
from scarlatti.utils import get_icon_name
from scarlatti.utils_file import create_dir


class SelectionListRowMenu(Gio.Menu):
    """
        A menu related to a selection list row
    """
    def __init__(self, rowid, header=False):
        """
            Init menu
            @param rowid as int
            @param header as bool
        """

        label = ShownLists.IDS[rowid]
        Gio.Menu.__init__(self)
        if header:
            from scarlatti.menu_header import MenuHeader
            icon_name = get_icon_name(rowid)
            self.append_item(MenuHeader(label, icon_name))

        # Startup menu
        if not App().settings.get_value("save-state"):
            startup_menu = Gio.Menu()
            selected = rowid == App().settings.get_value(
                "startup-id").get_int32()
            action = Gio.SimpleAction.new_stateful(
                                    "default_selection_id",
                                    None,
                                    GLib.Variant.new_boolean(selected))
            App().add_action(action)
            action.connect("change-state",
                           self.__on_default_change_state,
                           rowid)
            item = Gio.MenuItem.new(_("Default on startup"),
                                    "app.default_selection_id")
            startup_menu.append_item(item)
            self.append_section(_("Startup"), startup_menu)

        # Cache menu
        if label == "Information":
            cache_menu = Gio.Menu()
            selected = rowid == App().settings.get_value(
                "cache-id").get_int32()
            action = Gio.SimpleAction.new(
                                    "default_selection_id_2",
                                    None)
            App().add_action(action)
            action.connect("activate",
                           self.__wipe_information_cache,
                           rowid)
            item = Gio.MenuItem.new(_("Wipe cache"),
                                    "app.default_selection_id_2")
            cache_menu.append_item(item)
            self.append_section(_("Cache"), cache_menu)

#######################
# PRIVATE             #
#######################
    def __on_default_change_state(self, action, variant, rowid):
        """
            Add to playlists
            @param action as Gio.SimpleAction
            @param variant as GVariant
            @param rowid as int
        """
        action.set_state(variant)
        if variant:
            App().settings.set_value("startup-id",
                                     GLib.Variant("i", rowid))
        else:
            App().settings.set_value("startup-id",
                                     GLib.Variant("i", -1))

    def __wipe_information_cache(self, action, variant, rowid):
        """
            Wipe the information cache
            @param action as Gio.SimpleAction
            @param variant as GVariant
            @param rowid as int
        """
        if os.path.exists(ARTIST_WIKI_PATH) and "/scarlatti/" in ARTIST_WIKI_PATH:
            shutil.rmtree(ARTIST_WIKI_PATH)
            create_dir(ARTIST_WIKI_PATH)
            App().window.container.show_notification(
                _("Successfully wiped the information cache."), [], [])
            GLib.timeout_add(2000, App().window.container.dismiss_notification)
        else:
            App().window.container.show_notification(
                _("An error occured while trying to wipe the cache."), [], [])


class SelectionListMenu(Gio.Menu):
    """
        A menu for configuring SelectionList
    """

    def __init__(self, widget, mask, header=False):
        """
            Init menu
            @param widget as Gtk.Widget
            @param mask as SelectionListMask
            @param header as bool
        """
        Gio.Menu.__init__(self)
        self.__widget = widget
        self.__mask = mask

        if header:
            from scarlatti.menu_header import MenuHeader
            if mask & SelectionListMask.PLAYLISTS:
                label = _("Playlists")
                icon_name = "emblem-documents-symbolic"
            else:
                label = _("Sidebar")
                icon_name = "org.scarlatti.Scarlatti-sidebar-symbolic"
            self.append_item(MenuHeader(label, icon_name))

        # Options
        if not App().window.folded and\
                not mask & SelectionListMask.PLAYLISTS:
            options_menu = Gio.Menu()
            action = Gio.SimpleAction.new_stateful(
                    "show_label",
                    None,
                    App().settings.get_value("show-sidebar-labels"))
            action.connect("change-state",
                           self.__on_show_label_change_state)
            App().add_action(action)
            options_menu.append(_("Show text"), "app.show_label")
            self.append_section(_("Options"), options_menu)

        # Shown menu
        shown_menu = Gio.Menu()
        if mask & SelectionListMask.PLAYLISTS:
            lists = ShownPlaylists.get(True)
            wanted = App().settings.get_value("shown-playlists")
        else:
            mask |= SelectionListMask.COMPILATIONS
            lists = ShownLists.get(mask, True)
            wanted = App().settings.get_value("shown-album-lists")
        for item in lists:
            if item[0] == Type.SEPARATOR:
                continue
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
        if variant and rowid not in wanted:
            wanted.append(rowid)
        elif rowid in wanted:
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
                startup_id = App().settings.get_value("startup-id")
                if startup_id == rowid:
                    App().settings.set_value("startup-id",
                                             GLib.Variant("i", -1))

    def __on_show_label_change_state(self, action, variant):
        """
            Update option
            @param action as Gio.SimpleAction
            @param variant as GVariant
        """
        action.set_state(variant)
        App().settings.set_value("show-sidebar-labels",
                                 GLib.Variant("b", variant))
