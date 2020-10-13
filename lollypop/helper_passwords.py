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
        Secret.Service.get(Secret.ServiceFlags.LOAD_COLLECTIONS, None,
                           self.__on_get_secret)

    def get_token(self, service):
        """
            Get token for service
            @param service as str
        """
        try:
            secret = Secret.Service.get_sync(Secret.ServiceFlags.NONE)
            SecretSchema = {
                "service": Secret.SchemaAttributeType.STRING
            }
            SecretAttributes = {
                "service": service
            }
            schema = Secret.Schema.new("org.gnome.Lollypop",
                                       Secret.SchemaFlags.NONE,
                                       SecretSchema)
            items = secret.search_sync(schema, SecretAttributes,
                                       Secret.SearchFlags.UNLOCK |
                                       Secret.SearchFlags.LOAD_SECRETS,
                                       None)
            if items:
                items[0].load_secret_sync(None)
                value = items[0].get_secret()
                if value is not None:
                    return value.get_text()
        except Exception as e:
            Logger.error("PasswordsHelper::get_sync(): %s" % e)
        return None

    def get(self, service, callback, *args):
        """
            Get password
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
                                 Secret.SearchFlags.UNLOCK |
                                 Secret.SearchFlags.LOAD_SECRETS,
                                 None,
                                 self.__on_secret_search,
                                 service,
                                 callback,
                                 *args)
        except Exception as e:
            Logger.warning("PasswordsHelper::get(): %s" % e)

    def store(self, service, login, password, callback=None, *args):
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
            Logger.warning("PasswordsHelper::store(): %s" % e)

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
                                 Secret.SearchFlags.UNLOCK |
                                 Secret.SearchFlags.LOAD_SECRETS,
                                 None,
                                 self.__on_clear_search,
                                 callback,
                                 *args)
        except Exception as e:
            Logger.warning("PasswordsHelper::clear(): %s" % e)

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
            Logger.error("PasswordsHelper::__on_clear_search(): %s" % e)

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
                    attributes = item.get_attributes()
                    secret = item.get_secret()
                    callback(attributes,
                             secret.get().decode('utf-8'),
                             service,
                             *args)
                    break
            else:
                Logger.info("PasswordsHelper: no result!")
                callback(None, None, service, *args)
        except Exception as e:
            Logger.error("PasswordsHelper::__on_secret_search(): %s" % e)
            callback(None, None, service, *args)

    def __on_get_secret(self, source, result):
        """
            Store secret proxy
            @param source as GObject.Object
            @param result as Gio.AsyncResult
        """
        try:
            self.__secret = source.get_finish(result)
            self.__secret.unlock(self.__secret.get_collections())
        except Exception as e:
            self.__secret = -1
            Logger.error("PasswordsHelper::__on_get_secret(): %s" % e)
