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
gi.require_version("Soup", "2.4")
from gi.repository import GLib, Soup

from threading import Thread

from lollypop.define import App
from lollypop.logger import Logger


class TaskHelper:
    """
        Simple helper for running a task in background
    """

    def __init__(self):
        """
            Init helper
        """
        self.__headers = []

    def add_header(self, name, value):
        """
            Add header
            @param name as str
            @param value as str
        """
        self.__headers.append((name, value))

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
        try:
            session = Soup.Session.new()
            session.set_property('accept-language-auto', True)
            # Post message
            if self.__headers:
                msg = Soup.Message.new("GET", uri)
                headers = msg.get_property("request-headers")
                for header in self.__headers:
                    headers.append(header[0],
                                   header[1])
                session.send_async(msg, cancellable,
                                   self.__on_load_uri_content,
                                   callback, cancellable, uri, *args)
            # Get message
            else:
                request = session.request(uri)
                request.send_async(cancellable,
                                   self.__on_request_send_async,
                                   callback,
                                   cancellable,
                                   uri,
                                   *args)
        except Exception as e:
            Logger.error("HelperTask::load_uri_content(): %s" % e)
            callback(uri, False, b"", *args)

    def load_uri_content_sync(self, uri, cancellable=None):
        """
            Load uri
            @param uri as str
            @param cancellable as Gio.Cancellable
            @return (loaded as bool, content as bytes)
        """
        try:
            session = Soup.Session.new()
            session.set_property(
                "user-agent",
                "Lollypop/%s (cedric.bellegarde@adishatz.org)" % App().version)
            # Set headers
            if self.__headers:
                msg = Soup.Message.new("GET", uri)
                headers = msg.get_property("request-headers")
                for header in self.__headers:
                    headers.append(header[0],
                                   header[1])
                session.send_message(msg)
                body = msg.get_property("response-body")
                bytes = body.flatten().get_data()
            # Get message
            else:
                request = session.request(uri)
                stream = request.send(cancellable)
                bytes = bytearray(0)
                buf = stream.read_bytes(1024, cancellable).get_data()
                while buf:
                    bytes += buf
                    buf = stream.read_bytes(1024, cancellable).get_data()
                stream.close()
            return (True, bytes)
        except Exception as e:
            Logger.error("TaskHelper::load_uri_content_sync(): %s" % e)
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
            session = Soup.Session.new()
            session.send_async(message,
                               cancellable,
                               self.__on_message_send_async,
                               callback,
                               cancellable,
                               message.get_uri(),
                               *args)
        except Exception as e:
            Logger.error("TaskHelper::send_message(): %s" % e)

#######################
# PRIVATE             #
#######################
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
            Logger.error("TaskHelper::__run(): %s: %s -> %s"
                         % (e, command, kwd))

    def __on_read_bytes_async(self, stream, result, content,
                              cancellable, callback, uri, *args):
        """
            Read data from stream, when finished, pass to callback
            @param stream as Gio.InputStream
            @param result as Gio.AsyncResult
            @param cancellable as Gio.Cancellable
            @param content as bytes
            @param callback as function
            @param uri as str
        """
        try:
            content_result = stream.read_bytes_finish(result)
            content_bytes = content_result.get_data()
            if content_bytes:
                content += content_bytes
                stream.read_bytes_async(4096, GLib.PRIORITY_LOW,
                                        cancellable,
                                        self.__on_read_bytes_async,
                                        content, cancellable, callback,
                                        uri, *args)
            else:
                callback(uri, True, bytes(content), *args)
        except Exception as e:
            Logger.error("TaskHelper::__on_read_bytes_async(): %s" % e)
            callback(uri, False, b"", *args)

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
            Logger.error("TaskHelper::__on_soup_msg_finished(): %s" % e)
            callback(uri, False, b"", *args)

    def __on_message_send_async(self, source, result, callback,
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
            Logger.error("TaskHelper::__on_soup_msg_finished(): %s" % e)
            callback(uri, False, b"", *args)

    def __on_load_uri_content(self, source, result, callback,
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
            Logger.error("TaskHelper::__on_soup_msg_finished(): %s" % e)
