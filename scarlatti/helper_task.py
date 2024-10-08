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

import gi
gi.require_version("Soup", "3.0")
from gi.repository import GLib, Soup

from threading import Thread
from urllib.parse import urlparse
from time import time, sleep

from scarlatti.define import App
from scarlatti.logger import Logger


class TaskHelper:
    """
        Simple helper for running a task in background
    """

    def __init__(self):
        """
            Init helper
        """
        self.__ratelimit = {}
        self.__retries = {}

    def run(self, command, *args, **kwargs):
        """
            Run command with params and return to callback
            @param command as function
            @param *args as command arguments
            @param **kwargs
            @return thread as Thread
        """
        thread = Thread(target=self.__run,
                        args=(command, kwargs, *args))
        thread.daemon = True
        thread.start()
        return thread

    def load_uri_content(self, uri, cancellable, callback, *args):
        """
            Load uri content async
            @param uri as str
            @param cancellable as Gio.Cancellable
            @param callback as a function
            @callback (uri as str, status as bool, content as bytes, args)
        """
        self.load_uri_content_with_headers(uri, [], cancellable,
                                           callback, *args)

    def load_uri_content_with_headers(self, uri, headers, cancellable,
                                      callback, *args):
        """
            Load uri content async with headers
            @param uri as str
            @param headers as []
            @param cancellable as Gio.Cancellable
            @param callback as a function
            @callback (uri as str, status as bool, content as bytes, args)
        """
        if cancellable is not None and cancellable.is_cancelled():
            callback(uri, False, b"", *args)
        try:
            delay = self.__get_delay_for_uri(uri)
            if delay > 0:
                GLib.timeout_add_seconds(
                                 delay,
                                 self.load_uri_content_with_headers,
                                 uri, headers, cancellable,
                                 callback, *args)
                return

            session = Soup.Session.new()
            session.set_property('accept-language-auto', True)
            session.set_property(
                "user-agent",
                "Scarlatti/%s (cedric.bellegarde@adishatz.org)" % App().version)
            msg = Soup.Message.new("GET", uri)
            if headers:
                headers = msg.get_property("request-headers")
                for header in headers:
                    headers.append(header[0],
                                   header[1])
            session.send_and_read_async(
                               msg, 0, cancellable,
                               self.__on_load_uri_content, msg, headers,
                               callback, cancellable, uri, *args)
        except Exception as e:
            Logger.warning(
                "HelperTask::load_uri_content_with_headers(): %s" % e)
            callback(uri, False, b"", *args)

    def load_uri_content_sync(self, uri, cancellable=None):
        """
            Load uri
            @param uri as str
            @param cancellable as Gio.Cancellable
            @return (loaded as bool, content as bytes)
        """
        return self.load_uri_content_sync_with_headers(uri, [], cancellable)

    def load_uri_content_sync_with_headers(self, uri, headers,
                                           cancellable=None):
        """
            Load uri
            @param uri as str
            @param headers as []
            @param cancellable as Gio.Cancellable
            @return (loaded as bool, content as bytes)
        """
        try:
            delay = self.__get_delay_for_uri(uri)
            if delay > 0:
                sleep(delay)
                if cancellable is not None and cancellable.is_cancelled():
                    return (False, b"")

            session = Soup.Session.new()
            session.set_property('accept-language-auto', True)
            session.set_property(
                "user-agent",
                "Scarlatti/%s (cedric.bellegarde@adishatz.org)" % App().version)
            msg = Soup.Message.new("GET", uri)
            if headers:
                request_headers = msg.get_property("request-headers")
                for header in headers:
                    request_headers.append(header[0], header[1])
            bytes = session.send_and_read(msg, cancellable).get_data()
            if bytes is None:
                response_headers = msg.get_property("response-headers")
                wait = self.__handle_ratelimit(response_headers, uri)
                if wait is not None:
                    retries = self.__get_retries_for_uri(uri)
                    if retries < 5:
                        parsed = urlparse(uri)
                        self.__ratelimit[parsed.netloc] = wait
                        return self.load_uri_content_sync_with_headers(
                            uri, headers, cancellable)
                    else:
                        del self.__retries[uri]
            else:
                return (True, bytes)
        except Exception as e:
            Logger.warning(
                "TaskHelper::load_uri_content_sync_with_headers(): %s" % e)
            return (False, b"")

    def send_message(self, message, cancellable, callback, *args):
        """
            Send message async
            @param message as Soup.Message
            @param cancellable as Gio.Cancellable
            @param callback as a function
            @callback (uri as str, status as bool, content as bytes, args)
        """
        try:
            uri = message.get_uri().to_string(False)
            delay = self.__get_delay_for_uri(uri)
            if delay > 0:
                GLib.timeout_add_seconds(delay,
                                         self.send_message,
                                         message, cancellable,
                                         callback, *args)
                return

            session = Soup.Session.new()
            session.send_and_read_async(
                               message,
                               0,
                               cancellable,
                               self.__on_message_send_async,
                               message,
                               callback,
                               cancellable,
                               uri,
                               *args)
        except Exception as e:
            Logger.warning("TaskHelper::send_message(): %s" % e)

    def send_message_sync(self, message, cancellable):
        """
            Send message sync
            @param message as Soup.Message
            @param cancellable as Gio.Cancellable
            @return bytes
        """
        try:
            uri = message.get_uri().to_string()
            delay = self.__get_delay_for_uri(uri)
            if delay > 0:
                sleep(delay)
                if cancellable is not None and cancellable.is_cancelled():
                    return None

            session = Soup.Session.new()
            bytes = session.send_and_read(message, cancellable).get_data()
            if bytes is None:
                response_headers = message.get_property("response-headers")
                wait = self.__handle_ratelimit(response_headers, uri)
                if wait is not None:
                    retries = self.__get_retries_for_uri(uri)
                    if retries < 5:
                        parsed = urlparse(uri)
                        self.__ratelimit[parsed.netloc] = wait
                        return self.send_message_sync(message, cancellable)
                    else:
                        del self.__retries[uri]
            else:
                return bytes
        except Exception as e:
            Logger.warning("TaskHelper::send_message_sync(): %s" % e)
        return None

#######################
# PRIVATE             #
#######################
    def __get_delay_for_uri(self, uri):
        """
            Get delay for last ratelimit
            @param uri as str
            @return int
        """
        delay = 0
        now = time()
        parsed = urlparse(uri)
        if parsed.netloc in self.__ratelimit.keys():
            wait = self.__ratelimit[parsed.netloc]
            delay = wait - now
            if delay < 0:
                del self.__ratelimit[parsed.netloc]
        return delay

    def __get_retries_for_uri(self, uri):
        """
            Get retries for uri
            @param uri as str
            @return int
        """
        retries = 0
        if uri in self.__retries.keys():
            retries = self.__retries[uri]
        else:
            self.__retries[uri] = 0
        return retries

    def __handle_ratelimit(self, response, uri):
        """
            Set rate limit from response
            @param response as Soup.MessageHeaders
            @param uri as str
            @return next_time as int
        """
        remaining_keys = ["X-RateLimit-Remaining", "X-Rate-Limit-Remaining"]
        reset_keys = ["X-RateLimit-Reset", "X-Rate-Limit-Reset",
                      "X-RateLimit-Reset-In", "X-RateLimit-Reset-At"]
        for key in remaining_keys:
            remaining = response.get_one(key)
            if remaining is not None:
                break
        for key in reset_keys:
            reset = response.get_one(key)
            if reset is not None:
                break
        if remaining is None or reset is None:
            return None
        # No more request available
        if (int(remaining) < 1):
            Logger.info(uri)
            Logger.info("X-RateLimit-Remaining: %s" % remaining)
            Logger.info("X-RateLimit-Reset: %s" % reset)
            return int(reset)

        if uri in self.__retries.keys():
            del self.__retries[uri]
        return None

    def __run(self, command, kwd, *args):
        """
            Pass command result to callback
            @param command as function
            @param *args as command arguments
            @param kwd as { "callback": (function, *args) }
        """
        try:
            result = command(*args)
            if "callback" in kwd.keys():
                (callback, *callback_args) = kwd["callback"]
                if callback is not None:
                    GLib.idle_add(callback, result, *callback_args)
        except Exception as e:
            Logger.warning("TaskHelper::__run(): %s: %s -> %s" %
                           (e, command, kwd))

    def __on_request_send_async(self, source, result, callback,
                                cancellable, uri, *args):
        """
            Get stream and start reading from it
            @param source as Soup.Session
            @param result as Gio.AsyncResult
            @param cancellable as Gio.Cancellable
            @param callback as a function
            @param uri as str
        """
        try:
            stream = source.send_finish(result)
            # We use a bytearray here as seems that bytes += is really slow
            stream.read_bytes_async(4096, GLib.PRIORITY_LOW,
                                    cancellable, self.__on_read_bytes_async,
                                    bytearray(0), cancellable, callback, uri,
                                    *args)
        except Exception as e:
            Logger.warning("TaskHelper::__on_soup_msg_finished(): %s" % e)
            callback(uri, False, b"", *args)

    def __on_message_send_async(self, source, result, message, callback,
                                cancellable, uri, *args):
        """
            Get stream and start reading from it
            @param source as Soup.Session
            @param result as Gio.AsyncResult
            @param message as Soup.Message
            @param cancellable as Gio.Cancellable
            @param callback as a function
            @param uri as str
        """
        try:
            response_headers = message.get_property("response-headers")
            wait = self.__handle_ratelimit(response_headers, uri)
            if wait is None:
                bytes = source.send_and_read_finish(result).get_data()
                callback(uri, True, bytes, *args)
            else:
                parsed = urlparse(uri)
                self.__ratelimit[parsed.netloc] = wait
                retries = self.__get_retries_for_uri(uri)
                if retries < 5:
                    self.__retries[uri] += 1
                    self.send_message(message, cancellable, callback, *args)
                else:
                    del self.__retries[uri]
        except Exception as e:
            Logger.warning("TaskHelper::__on_soup_msg_finished(): %s" % e)
            callback(uri, False, b"", *args)

    def __on_load_uri_content(self, source, result, msg, headers, callback,
                              cancellable, uri, *args):
        """
            Get stream and start reading from it
            @param source as Soup.Session
            @param result as Gio.AsyncResult
            @param msg as Soup.Message
            @param headers as []
            @param cancellable as Gio.Cancellable
            @param callback as a function
            @param uri as str
        """
        try:
            response_headers = msg.get_property("response-headers")
            wait = self.__handle_ratelimit(response_headers, uri)
            if wait is None:
                bytes = source.send_and_read_finish(result).get_data()
                callback(uri, True, bytes, *args)
            else:
                parsed = urlparse(uri)
                self.__ratelimit[parsed.netloc] = wait
                retries = self.__get_retries_for_uri(uri)
                if retries < 5:
                    self.__retries[uri] += 1
                    self.load_uri_content_sync_with_headers(uri, headers,
                                                            callback, *args)
                else:
                    del self.__retries[uri]
        except Exception as e:
            Logger.warning("TaskHelper::__on_soup_msg_finished(): %s" % e)
            callback(uri, False, b"", *args)
