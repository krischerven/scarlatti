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

from gi.repository import Gio, GLib, Gtk, Gdk

from gettext import gettext as _

from re import search as regex_search

from scarlatti.define import App, StorageType, CACHE_PATH
from scarlatti.objects_track import Track
from scarlatti.objects_album import Album
from scarlatti.logger import Logger
from scarlatti.dialog_apps import AppsDialog
from scarlatti.utils import copy_to_clipboard


class ActionsMenu(Gio.Menu):
    """
        ActionsMenu menu for albums and tracks
    """

    def __init__(self, object):
        """
            Init edit menu
            @param object as Album/Track
        """
        Gio.Menu.__init__(self)
        # Ignore genre_ids/artist_ids
        if isinstance(object, Album):
            self.__object = Album(object.id)
        else:
            self.__object = Track(object.id)
        self.__set_save_action()
        if self.__object.storage_type & StorageType.COLLECTION and\
                not GLib.file_test("/app", GLib.FileTest.EXISTS):
            self.__set_open_action()

        if isinstance(object, Track):
            self.__set_copy_source_url_to_clipboard_action()
            self.__set_open_source_url_action()
            self.__set_copy_title_to_clipboard_action()


#######################
# PRIVATE             #
#######################
    def __set_save_action(self):
        """
            Set save action
        """
        if not self.__object.storage_type & (StorageType.SAVED |
                                             StorageType.COLLECTION):
            save_action = Gio.SimpleAction(name="save_album_action")
            App().add_action(save_action)
            save_action.connect("activate",
                                self.__on_save_action_activate,
                                True)
            menu_item = Gio.MenuItem.new(_("Save in collection"),
                                         "app.save_album_action")
            menu_item.set_attribute_value("close", GLib.Variant("b", True))
            self.append_item(menu_item)
        elif self.__object.storage_type & StorageType.SAVED:
            save_action = Gio.SimpleAction(name="remove_album_action")
            App().add_action(save_action)
            save_action.connect("activate",
                                self.__on_save_action_activate,
                                False)
            menu_item = Gio.MenuItem.new(_("Remove from collection"),
                                         "app.remove_album_action")
            menu_item.set_attribute_value("close", GLib.Variant("b", True))
            self.append_item(menu_item)
        if self.__object.is_web:
            clean_action = Gio.SimpleAction(name="clean_album_action")
            App().add_action(clean_action)
            clean_action.connect("activate",
                                 self.__on_clean_action_activate)
            menu_item = Gio.MenuItem.new(_("Clean cache"),
                                         "app.clean_album_action")
            menu_item.set_attribute_value("close", GLib.Variant("b", True))
            self.append_item(menu_item)
        if isinstance(self.__object, Album) and\
                not self.__object.storage_type & StorageType.COLLECTION:
            buy_action = Gio.SimpleAction(name="buy_album_action")
            App().add_action(buy_action)
            buy_action.connect("activate",
                               self.__on_buy_action_activate)
            menu_item = Gio.MenuItem.new(_("Buy this album"),
                                         "app.buy_album_action")
            menu_item.set_attribute_value("close", GLib.Variant("b", True))
            self.append_item(menu_item)

    def __set_open_action(self):
        """
            Set edit action
        """
        open_tag_action = Gio.SimpleAction(name="open_tag_action")
        App().add_action(open_tag_action)
        open_tag_action.connect("activate", self.__on_open_tag_action_activate)
        menu_item = Gio.MenuItem.new(_("Open with…"),
                                     "app.open_tag_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)

    def __set_copy_source_url_to_clipboard_action(self):
        """
            Setup the open_source_url action
        """
        copy_source_url_to_clipboard_action = Gio.SimpleAction(name="copy_source_url_to_clipboard_action")
        App().add_action(copy_source_url_to_clipboard_action)
        copy_source_url_to_clipboard_action.connect("activate", self.__copy_source_url_to_clipboard)
        menu_item = Gio.MenuItem.new(_("Copy source URL"), "app.copy_source_url_to_clipboard_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)

    def __set_open_source_url_action(self):
        """
            Setup the open_source_url action
        """
        open_source_url_action = Gio.SimpleAction(name="open_source_url_action")
        App().add_action(open_source_url_action)
        open_source_url_action.connect("activate", self.__open_source_url)
        menu_item = Gio.MenuItem.new(_("Open source URL"), "app.open_source_url_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)

    def __set_copy_title_to_clipboard_action(self):
        """
            Setup the copy_title_to_clipboard action
        """
        copy_title_to_clipboard_action = Gio.SimpleAction(name="copy_title_to_clipboard_action")
        App().add_action(copy_title_to_clipboard_action)
        copy_title_to_clipboard_action.connect("activate", self.__copy_title_to_clipboard)
        menu_item = Gio.MenuItem.new(_("Copy title to clipboard"), "app.copy_title_to_clipboard_action")
        menu_item.set_attribute_value("close", GLib.Variant("b", True))
        self.append_item(menu_item)

    def __on_buy_action_activate(self, action, variant):
        """
            Launch a browser for Qobuz
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        artists = " ".join(self.__object.artists)
        search = "%s %s" % (artists, self.__object.name)
        uri = "https://www.qobuz.com/search?q=%s" % (
            GLib.uri_escape_string(search, None, True))
        Gtk.show_uri_on_window(App().window,
                               uri,
                               Gdk.CURRENT_TIME)

    def __on_clean_action_activate(self, action, variant):
        """
            clean album cache
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        try:
            if isinstance(self.__object, Album):
                tracks = self.__object.tracks
            else:
                tracks = [self.__object]
            for track in tracks:
                escaped = GLib.uri_escape_string(track.uri, None, True)
                f = Gio.File.new_for_path("%s/web_%s" % (CACHE_PATH, escaped))
                if f.query_exists():
                    f.delete(None)
        except Exception as e:
            Logger.error("ActionsMenu::__on_clean_action_activate():", e)

    def __on_save_action_activate(self, action, variant, save):
        """
            Save album to collection
            @param Gio.SimpleAction
            @param GLib.Variant
            @param save as bool
        """
        if isinstance(self.__object, Album):
            self.__object.save(save)
        else:
            album = self.__object.album
            album.save_track(save, self.__object)
        if not save:
            App().tracks.del_non_persistent()
            App().tracks.clean()
            App().albums.clean()
            App().artists.clean()
            App().genres.clean()

    def __on_open_tag_action_activate(self, action, variant):
        """
            Run tag editor
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        try:
            def launch_app(commandline, f):
                if f.query_exists():
                    args = []
                    for item in commandline.split():
                        if item in ["%U", "%u"]:
                            args.append(f.get_uri())
                        elif item in ["%F", "%f"]:
                            args.append(f.get_path())
                        else:
                            args.append(item)
                    commands = [args,
                                ["flatpak-spawn", "--host"] + args]
                    for cmd in commands:
                        try:
                            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                                cmd, flags=GLib.SpawnFlags.SEARCH_PATH |
                                GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
                                standard_input=False,
                                standard_output=False,
                                standard_error=False
                            )
                            GLib.spawn_close_pid(pid)
                            break
                        except Exception as e:
                            Logger.error("ActionsMenu::launch_app(): %s", e)

            def on_response(dialog, response_id, f):
                if response_id == Gtk.ResponseType.OK:
                    if dialog.commandline is not None:
                        launch_app(dialog.commandline, f)
                dialog.destroy()

            f = Gio.File.new_for_uri(self.__object.uri)
            dialog = AppsDialog(f)
            dialog.connect("response", on_response, f)
            dialog.run()
        except Exception as e:
            Logger.error("ActionsMenu::__on_open_tag_action_activate(): %s", e)

    def __get_source_url(self, action, variant):
        """
            Get the source (if any) of the selected track
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        ytdlp_1 = regex_search(r"\[([a-zA-Z0-9_\-]{11})\]", self.__object.title)
        ytdlp_2 = regex_search(r"-([a-zA-Z0-9_\-]{11})", self.__object.title)
        extracted = ytdlp_1 if ytdlp_1 else ytdlp_2
        if extracted:
            uid = extracted.group(1)
            return f"https://youtube.com/watch?v={uid}"
        return None

    def __open_source_url(self, action, variant):
        """
            Open the source (if any) of the selected track
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        url = self.__get_source_url(action, variant)
        if url:
            Gio.AppInfo.launch_default_for_uri(url, None)
        else:
            App().window.container.show_notification(_("No source URL was found in the track title"))

    def __copy_source_url_to_clipboard(self, action, variant):
        """
            Open the source (if any) of the selected track
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        url = self.__get_source_url(action, variant)
        if url:
            copy_to_clipboard(url)
            App().window.container.show_notification(_("Track source URL copied to clipboard"))
        else:
            App().window.container.show_notification(_("No source URL was found in the track title"))

    def __copy_title_to_clipboard(self, action, variant):
        """
            Open the source (if any) of the selected track
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        copy_to_clipboard(self.__object.title)
        App().window.container.show_notification(_("Track title copied to clipboard"))
