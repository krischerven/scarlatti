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

from gi.repository import Gtk, GLib

from lollypop.define import App


class BehaviourSettingsWidget(Gtk.Bin):
    """
        Widget allowing user to set behaviour options
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsBehaviour.ui")

        switch_scan = builder.get_object("switch_scan")
        switch_scan.set_state(App().settings.get_value("auto-update"))

        switch_background = builder.get_object("switch_background")
        switch_background.set_state(
            App().settings.get_value("background-mode"))

        switch_state = builder.get_object("switch_state")
        switch_state.set_state(App().settings.get_value("save-state"))

        switch_import = builder.get_object("switch_import")
        switch_import.set_state(App().settings.get_value("import-playlists"))

        switch_transitions = builder.get_object("switch_transitions")
        transitions = App().settings.get_value("transitions")
        switch_transitions.set_state(transitions)
        builder.get_object("button_transitions").set_sensitive(transitions)

        switch_transitions_party = builder.get_object(
            "switch_transitions_party")
        switch_transitions_party.set_state(
            App().settings.get_value("transitions-party-only"))

        switch_artwork_tags = builder.get_object("switch_artwork_tags")
        switch_artwork_tags.set_state(App().settings.get_value("save-to-tags"))

        self.__spin_transitions_duration = builder.get_object(
            "spin_transitions_duration")
        self.__spin_transitions_duration.set_range(250, 9000)
        self.__spin_transitions_duration.set_value(
            App().settings.get_value("transitions-duration").get_int32())

        replaygain_combo = builder.get_object("replaygain_combo")
        replaygain_combo.set_active(App().settings.get_enum(("replay-gain")))

        self.add(builder.get_object("widget"))
        builder.connect_signals(self)

#######################
# PROTECTED           #
#######################
    def _on_switch_scan_state_set(self, widget, state):
        """
            Update scan setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("auto-update",
                                 GLib.Variant("b", state))

    def _on_switch_background_state_set(self, widget, state):
        """
            Update background mode setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("background-mode",
                                 GLib.Variant("b", state))

    def _on_switch_state_state_set(self, widget, state):
        """
            Update save state setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-state",
                                 GLib.Variant("b", state))

    def _on_switch_import_state_set(self, widget, state):
        """
            Update save state setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("import-playlists",
                                 GLib.Variant("b", state))

    def _on_button_clicked(self, popover):
        """
            Show popover
            @param popover as Gtk.Popover
        """
        popover.popup()

    def _on_switch_transitions_state_set(self, widget, state):
        """
            Update smooth transitions setting
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("transitions", GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_switch_fade_state_set(self, widget, state):
        """
            Update smooth transitions setting
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("fade", GLib.Variant("b", state))

    def _on_switch_transitions_party_state_set(self, widget, state):
        """
            Update transitions party only setting
            @param widget as Gtk.Range
        """
        widget.set_sensitive(state)
        App().settings.set_value("transitions-party-only",
                                 GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_spin_transitions_duration_value_changed(self, widget):
        """
            Update mix duration setting
            @param widget as Gtk.Range
        """
        value = widget.get_value()
        App().settings.set_value("transitions-duration",
                                 GLib.Variant("i", value))

    def _on_switch_artwork_tags_state_set(self, widget, state):
        """
            Update artwork in tags setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-to-tags", GLib.Variant("b", state))

    def _on_combo_replaygain_by_changed(self, widget):
        """
            Update replaygain setting
            @param widget as Gtk.ComboBoxText
        """
        App().settings.set_enum("replay-gain", widget.get_active())
        for plugin in App().player.plugins:
            plugin.build_audiofilter()
        App().player.reload_track()

#######################
# PRIVATE             #
#######################
