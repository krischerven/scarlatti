# Copyright (c) 2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

import gi
gi.require_version('Secret', '1')
from gi.repository import Secret, GLib

from lollypop.logger import Logger


class PasswordsHelper:
    """
        Simpler helper for Secret
    """

    def __init__(self):
        """
            Init helper
        """
        self.__secret = None
        Secret.Service.get(Secret.ServiceFlags.NONE, None,
                           self.__on_get_secret)

    def get(self, service, callback, *args):
        """
            Call function
            @param service as str
            @param callback as function
            @param args
        """
        try:
            self.__wait_for_secret(self.get, service, callback, *args)
            SecretSchema = {
                "service": Secret.SchemaAttributeType.STRING
            }
            SecretAttributes = {
                "service": service
            }
            schema = Secret.Schema.new("org.gnome.Lollypop",
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            self.__secret.search(schema, SecretAttributes,
                                 Secret.SearchFlags.ALL,
                                 None,
                                 self.__on_secret_search,
                                 service,
                                 callback,
                                 *args)
        except Exception as e:
            Logger.debug("PasswordsHelper::get(): %s" % e)

    def store(self, service, login, password, callback, *args):
        """
            Store password
            @param service as str
            @param login as str
            @param password as str
            @param callback as function
        """
        try:
            self.__wait_for_secret(self.store,
                                   service,
                                   login,
                                   password,
                                   callback,
                                   *args)
            schema_string = "org.gnome.Lollypop: %s@%s" % (service, login)
            SecretSchema = {
                "service": Secret.SchemaAttributeType.STRING,
                "login": Secret.SchemaAttributeType.STRING,
            }
            SecretAttributes = {
                "service": service,
                "login": login
            }
            schema = Secret.Schema.new("org.gnome.Lollypop",
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            Secret.password_store(schema, SecretAttributes,
                                  Secret.COLLECTION_DEFAULT,
                                  schema_string,
                                  password,
                                  None,
                                  callback,
                                  *args)
        except Exception as e:
            Logger.debug("PasswordsHelper::store(): %s" % e)

    def clear(self, service, callback=None, *args):
        """
            Clear password
            @param service as str
            @param callback as function
        """
        try:
            self.__wait_for_secret(self.clear, service, callback, *args)
            SecretSchema = {
                "service": Secret.SchemaAttributeType.STRING
            }
            SecretAttributes = {
                "service": service
            }
            schema = Secret.Schema.new("org.gnome.Lollypop",
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            self.__secret.search(schema,
                                 SecretAttributes,
                                 Secret.SearchFlags.ALL,
                                 None,
                                 self.__on_clear_search,
                                 callback,
                                 *args)
        except Exception as e:
            Logger.debug("PasswordsHelper::clear(): %s" % e)

#######################
# PRIVATE             #
#######################
    def __wait_for_secret(self, call, *args):
        """
            Wait for secret
            @param call as function to call
            @param args
            @raise exception if waiting
        """
        # Wait for secret
        if self.__secret is None:
            GLib.timeout_add(250, call, *args)
            raise Exception("Waiting Secret service")
        elif self.__secret == -1:
            raise Exception("Error waiting for Secret service")

    def __on_clear_search(self, source, result, callback=None, *args):
        """
            Clear passwords
            @param source as GObject.Object
            @param result as Gio.AsyncResult
        """
        try:
            if result is not None:
                items = source.search_finish(result)
                for item in items:
                    item.delete(None, None)
            if callback is not None:
                callback(*args)
        except Exception as e:
            Logger.debug("PasswordsHelper::__on_clear_search(): %s" % e)

    def __on_load_secret(self, source, result, service, callback, *args):
        """
            Set userservice/password input
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param service as str
            @param index as int
            @param count as int
            @param callback as function
            @param args
        """
        secret = source.get_secret()
        if secret is not None:
            callback(source.get_attributes(),
                     secret.get().decode('utf-8'),
                     service,
                     *args)
        else:
            Logger.debug("PasswordsHelper: no secret!")
            callback(None, None, service, *args)

    def __on_secret_search(self, source, result, service, callback, *args):
        """
            Set userservice/password input
            @param source as GObject.Object
            @param result as Gio.AsyncResult
            @param service as str/None
            @param callback as function
            @param args
        """
        try:
            if result is not None:
                items = source.search_finish(result)
                for item in items:
                    item.load_secret(None,
                                     self.__on_load_secret,
                                     service,
                                     callback,
                                     *args)
                if not items:
                    Logger.debug("PasswordsHelper: no items!")
                    callback(None, None, service, *args)
            else:
                Logger.debug("PasswordsHelper: no result!")
                callback(None, None, service, *args)
        except Exception as e:
            Logger.debug("PasswordsHelper::__on_secret_search(): %s" % e)
            callback(None, None, service, *args)

    def __on_get_secret(self, source, result):
        """
            Store secret proxy
            @param source as GObject.Object
            @param result as Gio.AsyncResult
        """
        try:
            self.__secret = source.get_finish(result)
        except Exception as e:
            self.__secret = -1
            Logger.debug("PasswordsHelper::__on_get_secret(): %s" % e)
