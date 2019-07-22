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

from gettext import gettext as _

from lollypop.define import App
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

        if App().lastfm is not None and App().lastfm.is_goa:
            builder.get_object("lastfm_error_label").set_text(
                _('Using "GNOME Online Accounts" settings'))

        #
        # Google tab
        #
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        builder.get_object("cs-entry").set_text(key)

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
        if App().lastfm is not None:
            self.__lastfm_test_image = builder.get_object("lastfm_test_image")
            self.__lastfm_login = builder.get_object("lastfm_login")
            self.__lastfm_password = builder.get_object("lastfm_password")
            helper.get("lastfm",
                       self.__on_get_password)
            if not App().lastfm.is_goa:
                builder.get_object("lastfm_grid").set_sensitive(True)
                builder.get_object("lastfm_error_label").hide()
        #
        # Libre.fm tab
        #
        if App().lastfm is not None:
            self.__librefm_test_image = builder.get_object(
                "librefm_test_image")
            self.__librefm_login = builder.get_object("librefm_login")
            self.__librefm_password = builder.get_object("librefm_password")
            helper.get("librefm",
                       self.__on_get_password)
            builder.get_object("librefm_grid").set_sensitive(True)
            builder.get_object("librefm_error_label").hide()
        self.add(builder.get_object("widget"))
        builder.connect_signals(self)

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

#######################
# PRIVATE             #
#######################
    def __update_fm_settings(self, name):
        """
            Update *fm settings
            @param name as str (librefm/lastfm)
        """
        if App().lastfm is None:
            return
        from pylast import LastFMNetwork, LibreFMNetwork
        fm = None
        for scrobbler in App().scrobblers:
            if (isinstance(scrobbler, LibreFMNetwork) and
                name == "librefm") or\
                    (isinstance(scrobbler, LastFMNetwork) and
                     name != "librefm"):
                fm = scrobbler
                break
        if name == "librefm":
            callback = self.__test_librefm_connection
            login = self.__librefm_login.get_text()
            password = self.__librefm_password.get_text()
        elif App().lastfm is not None:
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
