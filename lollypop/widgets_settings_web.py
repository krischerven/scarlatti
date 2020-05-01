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

from gi.repository import Gtk, GLib, Gio, Gdk

from gettext import gettext as _

from lollypop.define import App, NetworkAccessACL
from lollypop.define import LASTFM_API_KEY
from lollypop.helper_passwords import PasswordsHelper
from lollypop.helper_signals import SignalsHelper, signals_map


class WebSettingsWidget(Gtk.Bin, SignalsHelper):
    """
        Widget allowing user to configure web providers
    """

    @signals_map
    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        self.__cancellable = Gio.Cancellable()
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsWeb.ui")

        self.__widgets = [(builder.get_object("listenbrainz_view"),
                           builder.get_object("listenbrainz_error_label"),
                           NetworkAccessACL["MUSICBRAINZ"],
                           False),
                          (builder.get_object("google_view"),
                           builder.get_object("google_error_label"),
                           None,
                           False)]

        # Web services access
        self.__acl_grid = builder.get_object("acl_grid")
        switch_network_access = builder.get_object("switch_network_access")
        network_access = App().settings.get_value("network-access")
        switch_network_access.set_state(network_access)
        self.__acl_grid.set_sensitive(network_access)
        acl = App().settings.get_value("network-access-acl").get_int32()
        for key in NetworkAccessACL.keys():
            if acl & NetworkAccessACL[key]:
                builder.get_object(key).set_state(True)

        #
        # Google tab
        #
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        self.__cs_entry = builder.get_object("cs-entry")
        self.__cs_entry.set_text(key)
        uri = App().settings.get_value("invidious-server").get_string()
        recent_youtube_dl = App().settings.get_value("recent-youtube-dl")
        self.__switch_youtube = builder.get_object("switch_youtube")
        self.__switch_youtube.set_state(recent_youtube_dl)
        entry_invidious = builder.get_object("entry_invidious")
        entry_invidious.set_text(uri)
        if uri:
            self.__switch_youtube.set_sensitive(False)

        #
        # ListenBrainz tab
        #
        token = App().settings.get_value(
            "listenbrainz-user-token").get_string()
        builder.get_object("listenbrainz_user_token_entry").set_text(token)

        self.add(builder.get_object("widget"))

        # Check web services access
        self.__check_acls()

        builder.connect_signals(self)
        self.connect("unmap", self.__on_unmap)

        self.__passwords_helper = PasswordsHelper()
        self.__passwords_helper.get("LASTFM", self.__on_get_password,
                                    builder.get_object("lastfm_button"))
        self.__passwords_helper.get("LIBREFM", self.__on_get_password,
                                    builder.get_object("librefm_button"))

        return [
            (App().settings, "changed::network-access",
             "_on_network_access_changed"),
            (App().settings, "changed::network-access-acl",
             "_on_network_access_changed"),
        ]

#######################
# PROTECTED           #
#######################
    def _on_entry_cs_changed(self, entry):
        """
            Save key
            @param entry as Gtk.Entry
        """
        value = entry.get_text().strip()
        App().settings.set_value("cs-api-key", GLib.Variant("s", value))

    def _on_entry_listenbrainz_token_changed(self, entry):
        """
            Save listenbrainz token
            @param entry as Gtk.Entry
        """
        value = entry.get_text().strip()
        App().settings.set_value("listenbrainz-user-token",
                                 GLib.Variant("s", value))

    def _on_lastfm_button_clicked(self, button):
        """
            Connect to lastfm
            @param button as Gtk.Button
        """
        if button.get_tooltip_text():
            button.set_tooltip_text("")
            button.set_label(_("Connect"))
            App().ws_director.token_ws.clear_token("LASTFM", True)
        else:
            button.set_sensitive(False)
            App().task_helper.run(self.__get_lastfm_token, button, "LASTFM")

    def _on_librefm_button_clicked(self, button):
        """
            Test librefm connection
            @param button as Gtk.Button
        """
        if button.get_tooltip_text():
            button.set_tooltip_text("")
            button.set_label(_("Connect"))
            App().ws_director.token_ws.clear_token("LIBREFM", True)
        else:
            button.set_sensitive(False)
            App().task_helper.run(self.__get_lastfm_token, button, "LIBREFM")

    def _on_switch_youtube_state_set(self, widget, state):
        """
            Update artist artwork setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("recent-youtube-dl",
                                 GLib.Variant("b", state))
        if Gio.NetworkMonitor.get_default().get_network_available() and state:
            from lollypop.utils_file import install_youtube_dl
            App().task_helper.run(install_youtube_dl)

    def _on_entry_invidious_changed(self, entry):
        """
            Update invidious server setting
            @param entry as Gtk.entry
        """
        uri = entry.get_text()
        App().settings.set_value("invidious-server", GLib.Variant("s", uri))
        self.__switch_youtube.set_sensitive(uri == "")

    def _on_enable_network_access_state_set(self, widget, state):
        """
            Save network access state
            @param widget as Gtk.Button
            @param state as bool
        """
        self.__acl_grid.set_sensitive(state)
        App().settings.set_value("network-access",
                                 GLib.Variant("b", state))

    def _on_enable_switch_state_set(self, widget, state):
        """
            Save network acl state
            @param widget as Gtk.Switch
            @param state as bool
        """
        key = widget.get_name()
        acl = App().settings.get_value("network-access-acl").get_int32()
        if state:
            acl |= NetworkAccessACL[key]
        else:
            acl &= ~NetworkAccessACL[key]
        acl = App().settings.set_value("network-access-acl",
                                       GLib.Variant("i", acl))

    def _on_network_access_changed(self, *ignore):
        self.__check_acls()

#######################
# PRIVATE             #
#######################
    def __get_lastfm_token(self, button, service):
        """
            Get Last.fm token
            @param button as Gtk.Button
            @param service as str
            @thread safe
        """
        def on_token(token, service):
            self.__passwords_helper.clear(service,
                                          self.__passwords_helper.store,
                                          service,
                                          service,
                                          token)
            validation_token = token.replace("validation:", "")
            if service == "LIBREFM":
                uri = "http://libre.fm/api/auth?api_key=%s&token=%s" % (
                    LASTFM_API_KEY, validation_token)
            else:
                uri = "http://www.last.fm/api/auth?api_key=%s&token=%s" % (
                    LASTFM_API_KEY, validation_token)
            GLib.idle_add(show_uri, uri)
            # Force web service to validate token
            App().ws_director.token_ws.clear_token(service)

        def show_uri(uri):
            Gtk.show_uri_on_window(App().window, uri, Gdk.CURRENT_TIME)

        App().ws_director.token_ws.clear_token(service, True)
        App().ws_director.token_ws.get_lastfm_auth_token(
            service, self.__cancellable, on_token)

    def __check_acls(self):
        """
            Check network ACLs
        """
        network_access = App().settings.get_value("network-access")
        acls = App().settings.get_value("network-access-acl").get_int32()
        for (view, label, acl, is_goa) in self.__widgets:
            if not network_access or (acl is not None and not acls & acl):
                view.set_sensitive(False)
                label.set_opacity(1)
                label.set_text(_("Disabled in network settings"))
            elif is_goa:
                view.set_sensitive(False)
                label.set_opacity(1)
                label.set_text(_('Using "GNOME Online Accounts" settings'))
            else:
                view.set_sensitive(True)
                label.set_opacity(0)
        self.__switch_youtube.set_sensitive(acls & NetworkAccessACL["YOUTUBE"])
        self.__cs_entry.set_sensitive(acls & NetworkAccessACL["YOUTUBE"] or
                                      acls & NetworkAccessACL["GOOGLE"])

    def __on_unmap(self, widget):
        """
            Cancel current tasks and clear token
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()

    def __on_get_password(self, attributes, password, service, button):
        """
            Set button state
            @param attributes as {}
            @param password as str
            @param service as str
            @param button as Gtk.Button
        """
        if attributes is not None:
            button.set_label(_("Disconnect"))
            button.set_tooltip_text(attributes["login"])
