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

from gi.repository import Gtk, GLib, Gio

from gettext import gettext as _

from lollypop.define import App, NetworkAccessACL
from lollypop.utils import get_network_available
from lollypop.logger import Logger


class WebSettingsWidget(Gtk.Bin):
    """
        Widget allowing user to configure web providers
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
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

        # First check lastfm support is available
        if App().lastfm is None:
            builder.get_object("lastfm_error_label").set_text(
                _("You need to install pylast and gi secret"))
            builder.get_object("librefm_error_label").set_text(
                _("You need to install pylast and gi secret"))
            builder.get_object("lastfm_error_label").set_opacity(1)
            builder.get_object("librefm_error_label").set_opacity(1)
            builder.get_object("lastfm_view").set_sensitive(False)
            builder.get_object("librefm_view").set_sensitive(False)

        else:
            self.__widgets += [(builder.get_object("lastfm_view"),
                                builder.get_object("lastfm_error_label"),
                                NetworkAccessACL["LASTFM"],
                                App().lastfm.is_goa),
                               (builder.get_object("librefm_view"),
                                builder.get_object("librefm_error_label"),
                                NetworkAccessACL["LASTFM"],
                                False)]

        # Check web services access
        self.__check_acls()

        #
        # Google tab
        #
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        builder.get_object("cs-entry").set_text(key)
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

        from lollypop.helper_passwords import PasswordsHelper
        helper = PasswordsHelper()

        #
        # Last.fm tab
        #
        self.__lastfm_test_image = builder.get_object("lastfm_test_image")
        self.__lastfm_login = builder.get_object("lastfm_login")
        self.__lastfm_password = builder.get_object("lastfm_password")
        helper.get("lastfm", self.__on_get_password)

        #
        # Libre.fm tab
        #
        self.__librefm_test_image = builder.get_object("librefm_test_image")
        self.__librefm_login = builder.get_object("librefm_login")
        self.__librefm_password = builder.get_object("librefm_password")
        helper.get("librefm", self.__on_get_password)

        self.add(builder.get_object("widget"))
        builder.connect_signals(self)
        App().settings.connect("changed::network-access",
                               lambda x, y: self.__check_acls())
        App().settings.connect("changed::network-access-acl",
                               lambda x, y: self.__check_acls())

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
        App().load_listenbrainz()

    def _on_lastfm_test_btn_clicked(self, button):
        """
            Test lastfm connection
            @param button as Gtk.Button
        """
        self.__update_fm_settings("lastfm")
        if not get_network_available():
            self.__lastfm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)
            return

    def _on_librefm_test_btn_clicked(self, button):
        """
            Test librefm connection
            @param button as Gtk.Button
        """
        self.__update_fm_settings("librefm")
        if not get_network_available():
            self.__librefm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)
            return

    def _on_switch_youtube_state_set(self, widget, state):
        """
            Update artist artwork setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("recent-youtube-dl",
                                 GLib.Variant("b", state))
        if Gio.NetworkMonitor.get_default().get_network_available() and state:
            from lollypop.utils import install_youtube_dl
            App().task_helper.run(install_youtube_dl)

    def _on_entry_invidious_changed(self, entry):
        """
            Update invidious server setting
            @param entry as Gtk.entry
        """
        uri = entry.get_text()
        App().settings.set_value("invidious-server", GLib.Variant("s", uri))
        self.__switch_youtube.set_sensitive(uri == "")

#######################
# PRIVATE             #
#######################
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

    def __update_fm_settings(self, name):
        """
            Update *fm settings
            @param name as str (librefm/lastfm)
        """
        fm = None
        for scrobbler in App().scrobblers:
            if scrobbler.service_name == name:
                fm = scrobbler
                break
        if fm is None:
            return
        elif name == "librefm":
            callback = self.__test_librefm_connection
            login = self.__librefm_login.get_text()
            password = self.__librefm_password.get_text()
        else:
            callback = self.__test_lastfm_connection
            login = self.__lastfm_login.get_text()
            password = self.__lastfm_password.get_text()
        try:
            if fm is not None and login and password:
                from lollypop.helper_passwords import PasswordsHelper
                helper = PasswordsHelper()
                helper.clear(name,
                             helper.store,
                             name,
                             login,
                             password,
                             self.__on_password_store,
                             fm,
                             callback)
        except Exception as e:
            Logger.error("SettingsDialog::__update_fm_settings(): %s" % e)

    def __test_lastfm_connection(self, result, fm):
        """
            Test lastfm connection
            @param result as None
            @param fm as LastFM
        """
        if fm.available:
            self.__lastfm_test_image.set_from_icon_name(
                "object-select-symbolic",
                Gtk.IconSize.MENU)
        else:
            self.__lastfm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)

    def __test_librefm_connection(self, result, fm):
        """
            Test librefm connection
            @param result as None
            @param fm as LastFM
        """
        if fm.available:
            self.__librefm_test_image.set_from_icon_name(
                "object-select-symbolic",
                Gtk.IconSize.MENU)
        else:
            self.__librefm_test_image.set_from_icon_name(
                "computer-fail-symbolic",
                Gtk.IconSize.MENU)

    def __on_password_store(self, source, result, fm, callback):
        """
            Connect service
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param fm as LastFM
            @param callback as function
        """
        fm.connect_service(True, callback, fm)

    def __on_get_password(self, attributes, password, name):
        """
             Set password label
             @param attributes as {}
             @param password as str
             @param name as str
        """
        if attributes is None:
            return
        if name == "librefm":
            self.__librefm_login.set_text(attributes["login"])
            self.__librefm_password.set_text(password)
        else:
            self.__lastfm_login.set_text(attributes["login"])
            self.__lastfm_password.set_text(password)
