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

from gi.repository import Gtk, GLib

from lollypop.define import App


class AppearanceSettingsWidget(Gtk.Bin):
    """
        Widget allowing user to set appearance options
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        self.__cover_tid = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsAppearance.ui")

        switch_view = builder.get_object("switch_dark")
        if App().gtk_application_prefer_dark_theme:
            switch_view.set_sensitive(False)
        else:
            switch_view.set_state(App().settings.get_value("dark-ui"))

        switch_compilations = builder.get_object("switch_compilations")
        switch_compilations_in_album_view = builder.get_object(
            "switch_compilations_in_album_view")
        switch_compilations_in_album_view.set_state(
            App().settings.get_value("show-compilations-in-album-view"))

        show_compilations = App().settings.get_value("show-compilations")
        switch_compilations.set_state(show_compilations)
        builder.get_object("compilations_button").set_sensitive(
            show_compilations)

        self.__popover_compilations = builder.get_object(
            "popover-compilations")

        switch_artwork = builder.get_object("switch_artwork")
        switch_artwork.set_state(App().settings.get_value("artist-artwork"))

        orderby_combo = builder.get_object("orderby_combo")
        orderby_combo.set_active(App().settings.get_enum(("orderby")))

        scale_coversize = builder.get_object("scale_coversize")
        scale_coversize.set_range(170, 300)
        scale_coversize.set_value(
            App().settings.get_value("cover-size").get_int32())
        self.add(builder.get_object("widget"))
        builder.connect_signals(self)

#######################
# PROTECTED           #
#######################
    def _on_compilations_button_clicked(self, widget):
        """
            Show compilations popover
            @param widget as Gtk.Button
        """
        self.__popover_compilations.popup()

    def _on_switch_compilations_state_set(self, widget, state):
        """
            Update show compilations setting
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("show-compilations",
                                 GLib.Variant("b", state))

    def _on_switch_compilations_in_album_view_state_set(self, widget, state):
        """
            Update show compilations in album view setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("show-compilations-in-album-view",
                                 GLib.Variant("b", state))

    def _on_switch_artwork_state_set(self, widget, state):
        """
            Update recent-youtube-dl setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("artist-artwork",
                                 GLib.Variant("b", state))
        if state:
            App().art.cache_artists_artwork()

    def _on_combo_order_by_changed(self, widget):
        """
            Update orderby setting
            @param widget as Gtk.ComboBoxText
        """
        App().settings.set_enum("orderby", widget.get_active())

    def _on_scale_coversize_value_changed(self, widget):
        """
            Delayed update cover size
            @param widget as Gtk.Range
        """
        if self.__cover_tid is not None:
            GLib.source_remove(self.__cover_tid)
            self.__cover_tid = None
        self.__cover_tid = GLib.timeout_add(500,
                                            self.__really_update_coversize,
                                            widget)

    def _on_switch_dark_state_set(self, widget, state):
        """
            Update view setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("dark-ui", GLib.Variant("b", state))
        if not App().player.is_party:
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", state)

    def _on_clean_artwork_cache_clicked(self, button):
        """
            Clean artwork cache
            @param button as Gtk.Button
        """
        App().task_helper.run(App().art.clean_all_cache)
        button.set_sensitive(False)

#######################
# PRIVATE             #
#######################
    def __really_update_coversize(self, widget):
        """
            Update cover size
            @param widget as Gtk.Range
        """
        self.__cover_tid = None
        App().task_helper.run(App().art.clean_all_cache)
        value = widget.get_value()
        App().settings.set_value("cover-size", GLib.Variant("i", value))
        App().art.update_art_size()
        App().window.container.reload_view()
