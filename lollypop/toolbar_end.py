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

from gi.repository import Gtk, Gio, GLib

from gettext import gettext as _

from lollypop.pop_appmenu import AppMenuPopover
from lollypop.pop_devices import DevicesPopover
from lollypop.define import App, Shuffle, Repeat
from lollypop.progressbar import ButtonProgressBar


class ToolbarEnd(Gtk.Bin):
    """
        Toolbar end
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        self.set_hexpand(True)
        self.__search_popover = None
        self.__devices_popover = None
        self.__timeout_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarEnd.ui")
        self.__party_submenu = builder.get_object("party_submenu")
        self.add(builder.get_object("end"))

        # Map some settings to actions, can't use Gio.Settings.create_action()
        # because API does not support set_enabled()
        self.__shuffle_action = Gio.SimpleAction.new_stateful(
            "shuffle",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "none"))
        self.__shuffle_action.set_state(App().settings.get_value("shuffle"))
        self.__shuffle_action.connect("change-state",
                                      self.__on_shuffle_change_state)
        self.__repeat_action = Gio.SimpleAction.new_stateful(
            "repeat",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "none"))
        self.__repeat_action.set_state(App().settings.get_value("repeat"))
        self.__repeat_action.connect("change-state",
                                     self.__on_repeat_change_state)
        App().add_action(self.__shuffle_action)
        App().add_action(self.__repeat_action)

        self.__shuffle_button = builder.get_object("shuffle_button")
        self.__shuffle_button_image = builder.get_object(
            "shuffle_button_image")
        shuffle_button_action = Gio.SimpleAction.new("shuffle-button", None)
        shuffle_button_action.connect("activate",
                                      self.__on_shuffle_button_activate)
        App().add_action(shuffle_button_action)
        App().set_accels_for_action("app.shuffle-button", ["<Control>r"])
        App().settings.connect("changed::shuffle", self.__on_repeat_changed)
        App().settings.connect("changed::repeat", self.__on_repeat_changed)

        party_action = Gio.SimpleAction.new_stateful(
            "party",
            None,
            GLib.Variant.new_boolean(App().player.is_party))
        party_action.connect("change-state", self.__on_party_mode_change_state)
        App().add_action(party_action)
        App().set_accels_for_action("app.party", ["<Control>p"])

        scrobbling_disabled = App().settings.get_value("disable-scrobbling")
        scrobbling_action = Gio.SimpleAction.new_stateful(
            "scrobbling",
            None,
            GLib.Variant.new_boolean(not scrobbling_disabled))
        scrobbling_action.connect("change-state",
                                  self.__on_scrobbling_mode_change_state)
        App().add_action(scrobbling_action)
        App().set_accels_for_action("app.scrobbling", ["<Control><Shift>s"])

        self.__search_button = builder.get_object("search_button")

        search_action = App().lookup_action("search")
        search_action.connect("activate", self.__on_search_activate)

        self.__list_button = builder.get_object("list_button")
        self.__list_button.set_property("has-tooltip", True)
        self.__list_button.connect("query-tooltip",
                                   self.__on_list_button_query_tooltip)
        self.__home_button = builder.get_object("home_button")
        App().player.connect("playlist-changed", self.__on_playlist_changed)
        self.__set_shuffle_icon()

        button_progress_bar = ButtonProgressBar()
        overlay = builder.get_object("overlay")
        overlay.add_overlay(button_progress_bar)
        overlay.set_overlay_pass_through(button_progress_bar, True)
        devices_button = builder.get_object("devices_button")
        self.__devices_popover = DevicesPopover(button_progress_bar)
        self.__devices_popover.connect(
                "closed", self.__on_popover_closed, devices_button)
        self.__devices_popover.connect("content-changed",
                                       self.__on_devices_content_changed,
                                       devices_button)
        self.__devices_popover.populate()
        builder.connect_signals(self)

    def set_mini(self, mini):
        """
            Set mini mode
            @param mini as bool
        """
        if mini:
            self.__search_button.hide()
            self.__list_button.hide()
            self.__home_button.show()
        else:
            self.__search_button.show()
            self.__list_button.show()
            self.__home_button.hide()

    def search(self, search):
        """
            Search item
            @param search as str
        """
        self.__on_search_button_cancelled()
        self.__search_popover.set_text(search)

    @property
    def devices_popover(self):
        """
            Get Devices Popover
            @return AppMenuPopover
        """
        return self.__devices_popover

    @property
    def home_button(self):
        """
            Get home button
            @return Gtk.Button
        """
        return self.__home_button

#######################
# PROTECTED           #
#######################
    def _on_list_button_toggled(self, button):
        """
            Show current playback context popover
            @param button as Gtk.ToggleButton
        """
        if not button.get_active():
            return
        from lollypop.pop_current import CurrentPopover
        popover = CurrentPopover()
        popover.set_relative_to(button)
        popover.popup()
        popover.connect("closed", self.__on_popover_closed, button)
        return True

    def _on_home_button_clicked(self, button):
        """
            Go home in adaptive mode
            @param button as Gtk.Button
        """
        App().window.go_home()

    def _on_search_button_toggled(self, button):
        """
            Show search popover
            @param button as Gtk.ToggleButton
        """
        if button.get_active():
            if self.__search_popover is None:
                from lollypop.pop_search import SearchPopover
                self.__search_popover = SearchPopover()
                self.__search_popover.connect("closed",
                                              self.__on_popover_closed,
                                              button)
            self.__search_popover.set_relative_to(button)
            self.__search_popover.popup()

    def _on_shuffle_button_toggled(self, button):
        """
           Popup shuffle menu
           @param button as Gtk.ToggleButton
        """
        if button.get_active():
            # Create submenu "Configure party mode"
            self.__party_submenu.remove_all()
            self.__init_party_submenu()

    def _on_devices_button_toggled(self, button):
        """
           Create submenu
           @param button as Gtk.ToggleButton
        """
        if button.get_active():
            self.__devices_popover.set_relative_to(button)
            self.__devices_popover.popup()

    def _on_settings_button_toggled(self, button):
        """
           Popup application menu
           @param button as Gtk.ToggleButton
        """
        if button.get_active():
            appmenu_popover = AppMenuPopover()
            appmenu_popover.connect(
                "closed", self.__on_popover_closed, button)
            appmenu_popover.set_relative_to(button)
            appmenu_popover.popup()

#######################
# PRIVATE             #
#######################
    def __init_party_submenu(self):
        """
            Init party submenu with current ids
        """
        def on_change_state(action, value, genre_id):
            action.set_state(value)
            ids = list(App().settings.get_value("party-ids"))
            genre_ids = App().genres.get_ids()
            # Select all
            if genre_id is None:
                # Update others
                for genre_id in genre_ids:
                    action = App().lookup_action("genre_%s" % genre_id)
                    if action.get_state() != value:
                        action.set_state(value)
                ids = []
            # Party id added
            elif value:
                ids.append(genre_id)
            # Party id removed
            elif ids and len(party_ids) > 1:
                ids.remove(genre_id)
            # Initial value
            else:
                genre_ids.remove(genre_id)
            App().settings.set_value("party-ids", GLib.Variant("ai", ids))
            App().player.set_party_ids()
            App().player.set_next()

        party_ids = App().settings.get_value("party-ids")
        all_ids = App().genres.get_ids()
        all_selected = len(set(all_ids) & set(party_ids)) == len(all_ids) or\
            not party_ids
        action = Gio.SimpleAction.new_stateful(
                    "all_party_ids",
                    None,
                    GLib.Variant.new_boolean(all_selected))
        action.connect("change-state", on_change_state, None)
        App().add_action(action)
        item = Gio.MenuItem.new(_("All genres"), "app.all_party_ids")
        self.__party_submenu.append_item(item)
        i = 0
        # Hack, hack, hack
        submenu_name = _("Next")
        menu = self.__party_submenu
        for (genre_id, name, sortname) in App().genres.get():
            in_party_ids = not party_ids or genre_id in party_ids
            action_name = "genre_%s" % genre_id
            action = Gio.SimpleAction.new_stateful(
                action_name,
                None,
                GLib.Variant.new_boolean(in_party_ids))
            action.connect("change-state", on_change_state, genre_id)
            App().add_action(action)
            menu_str = name if len(name) < 20 else name[0:20] + "…"
            item = Gio.MenuItem.new(menu_str, "app.%s" % action_name)
            menu.append_item(item)
            if i > 10:
                submenu = Gio.Menu()
                item = Gio.MenuItem.new(submenu_name, None)
                submenu_name += " "
                item.set_submenu(submenu)
                menu.append_item(item)
                menu = submenu
                i = 0
            i += 1

    def __set_shuffle_icon(self):
        """
            Set shuffle icon
        """
        shuffle = App().settings.get_enum("shuffle")
        repeat = App().settings.get_enum("repeat")
        if repeat == Repeat.TRACK:
            self.__shuffle_button_image.get_style_context().remove_class(
                "selected")
            self.__shuffle_button_image.set_from_icon_name(
                "media-playlist-repeat-song-symbolic",
                Gtk.IconSize.SMALL_TOOLBAR)
        elif shuffle == Shuffle.NONE:
            self.__shuffle_button_image.get_style_context().remove_class(
                "selected")
            if repeat == Repeat.ALL:
                self.__shuffle_button_image.set_from_icon_name(
                    "media-playlist-repeat-symbolic",
                    Gtk.IconSize.SMALL_TOOLBAR)
            else:
                self.__shuffle_button_image.set_from_icon_name(
                    "media-playlist-consecutive-symbolic",
                    Gtk.IconSize.SMALL_TOOLBAR)
        else:
            self.__shuffle_button_image.set_from_icon_name(
                "media-playlist-shuffle-symbolic",
                Gtk.IconSize.SMALL_TOOLBAR)
            if shuffle == Shuffle.TRACKS:
                self.__shuffle_button_image.get_style_context().add_class(
                    "selected")
            else:
                self.__shuffle_button_image.get_style_context().remove_class(
                    "selected")

    def __on_party_mode_change_state(self, action, value):
        """
            Activate party mode
            @param action as Gio.SimpleAction
            @param value as bool
        """
        if not App().gtk_application_prefer_dark_theme and\
                not App().settings.get_value("dark-ui"):
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", value)
        App().player.set_party(value.get_boolean())
        action.set_state(value)
        self.__shuffle_action.set_enabled(not value)
        self.__repeat_action.set_enabled(not value)

    def __on_scrobbling_mode_change_state(self, action, value):
        """
            Change scrobbling option
            @param action as Gio.SimpleAction
            @param value as bool
        """
        action.set_state(value)
        App().settings.set_value("disable-scrobbling",
                                 GLib.Variant("b", not value))

    def __on_shuffle_change_state(self, action, value):
        """
            Update shuffle setting
            @param action as Gio.SimpleAction
            @param value as bool
        """
        App().settings.set_value("shuffle", value)
        action.set_state(value)

    def __on_repeat_change_state(self, action, value):
        """
            Update playback setting
            @param action as Gio.SimpleAction
            @param value as GLib.Variant
        """
        App().settings.set_value("repeat", value)
        action.set_state(value)

    def __on_shuffle_button_activate(self, action, param):
        """
            Activate shuffle button
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        self.__shuffle_button.set_active(
            not self.__shuffle_button.get_active())

    def __on_repeat_changed(self, settings, value):
        """
            Update shuffle icon
            @param settings as Gio.Settings
            @param value as GLib.Variant
        """
        self.__set_shuffle_icon()

    def __on_popover_closed(self, popover, button):
        """
            Restore button state
            @param popover as Popover
            @param button as Gtk.Button
        """
        button.set_active(False)

    def __on_search_activate(self, action, variant):
        """
            @param action as Gio.SimpleAction
            @param variant as GLib.Variant
        """
        search = variant.get_string()
        if self.__search_button.is_visible():
            self.__search_button.set_active(
                not self.__search_button.get_active())
            self.__search_popover.set_search(search)

    def __on_list_button_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        if App().player.queue:
            widget.set_tooltip_text(_("Queue"))
        else:
            widget.set_tooltip_text(_("Tracks"))

    def __on_playlist_changed(self, player):
        """
            Update playback button status
            @param player as Player
        """
        if player.albums:
            self.__list_button.set_sensitive(True)
        else:
            self.__list_button.set_sensitive(False)

    def __on_devices_content_changed(self, popover, count, devices_button):
        """
            Hide/Show button
            @param popover as DevicesPopover
            @param count as int
            @param devices_button as Gtk.ToggleButton
        """
        if count:
            devices_button.show()
        else:
            devices_button.hide()
