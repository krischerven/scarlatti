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

import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GstAudio", "1.0")
gi.require_version("GstPbutils", "1.0")
gi.require_version("TotemPlParser", "1.0")
gi.require_version("Handy", "1")
from gi.repository import Gtk, Gio, GLib, Gdk, Gst, GstPbutils, Handy
Gst.init(None)
GstPbutils.pb_utils_init()

from threading import current_thread
from pickle import dump
from signal import signal, SIGINT, SIGTERM
from urllib.parse import urlparse

from lollypop.utils import init_proxy_from_gnome, emit_signal
from lollypop.application_actions import ApplicationActions
from lollypop.utils_file import get_file_type, install_youtube_dl
from lollypop.define import LOLLYPOP_DATA_PATH, ScanType, StorageType, FileType
from lollypop.database import Database
from lollypop.player import Player
from lollypop.inhibitor import Inhibitor
from lollypop.art import Art
from lollypop.logger import Logger
from lollypop.ws_director import DirectorWebService
from lollypop.sqlcursor import SqlCursor
from lollypop.settings import Settings
from lollypop.database_cache import CacheDatabase
from lollypop.database_albums import AlbumsDatabase
from lollypop.database_artists import ArtistsDatabase
from lollypop.database_genres import GenresDatabase
from lollypop.database_tracks import TracksDatabase
from lollypop.notification import NotificationManager
from lollypop.playlists import Playlists
from lollypop.objects_track import Track
from lollypop.objects_album import Album
from lollypop.helper_task import TaskHelper
from lollypop.helper_art import ArtHelper
from lollypop.collection_scanner import CollectionScanner


class Application(Gtk.Application, ApplicationActions):
    """
        Lollypop application:
            - Handle appmenu
            - Handle command line
            - Create main window
    """

    def __init__(self, version, data_dir):
        """
            Create application
            @param version as str
            @param data_dir as str
        """
        Gtk.Application.__init__(
            self,
            application_id="org.gnome.Lollypop",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.__version = version
        self.__data_dir = data_dir
        self.set_property("register-session", True)
        signal(SIGINT, lambda a, b: self.quit())
        signal(SIGTERM, lambda a, b: self.quit())
        # Set main thread name
        # We force it to current python 3.6 name, to be sure in case of
        # change in python
        current_thread().setName("MainThread")
        (self.__proxy_host, self.__proxy_port) = init_proxy_from_gnome()
        GLib.setenv("PULSE_PROP_media.role", "music", True)
        GLib.setenv("PULSE_PROP_application.icon_name",
                    "org.gnome.Lollypop", True)
        # Ideally, we will be able to delete this once Flatpak has a solution
        # for SSL certificate management inside of applications.
        if GLib.file_test("/app", GLib.FileTest.EXISTS):
            paths = ["/etc/ssl/certs/ca-certificates.crt",
                     "/etc/pki/tls/cert.pem",
                     "/etc/ssl/cert.pem"]
            for path in paths:
                if GLib.file_test(path, GLib.FileTest.EXISTS):
                    GLib.setenv("SSL_CERT_FILE", path, True)
                    break
        self.cursors = {}
        self.debug = False
        self.shown_sidebar_tooltip = False
        self.__window = None
        self.__fs_window = None
        settings = Gio.Settings.new("org.gnome.desktop.interface")
        self.animations = settings.get_value("enable-animations").get_boolean()
        GLib.set_application_name("Lollypop")
        GLib.set_prgname("lollypop")
        self.add_main_option("play-ids", b"a", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Play ids", None)
        self.add_main_option("debug", b"d", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Debug Lollypop", None)
        self.add_main_option("set-rating", b"r", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Rate the current track",
                             None)
        self.add_main_option("play-pause", b"t", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Toggle playback",
                             None)
        self.add_main_option("stop", b"s", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Stop playback",
                             None)
        self.add_main_option("next", b"n", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Go to next track",
                             None)
        self.add_main_option("prev", b"p", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Go to prev track",
                             None)
        self.add_main_option("emulate-phone", b"e", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE,
                             "Emulate a Librem phone",
                             None)
        self.add_main_option("version", b"v", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE,
                             "Lollypop version",
                             None)
        self.connect("command-line", self.__on_command_line)
        self.connect("handle-local-options", self.__on_handle_local_options)
        self.connect("activate", self.__on_activate)
        self.connect("shutdown", lambda a: self.__save_state())
        self.register(None)
        if self.get_is_remote():
            Gdk.notify_startup_complete()
        if GLib.environ_getenv(GLib.get_environ(), "DEBUG_LEAK") is not None:
            import gc
            gc.set_debug(gc.DEBUG_LEAK)

    def init(self):
        """
            Init main application
        """
        self.settings = Settings.new()
        # Mount enclosing volume as soon as possible
        uris = self.settings.get_music_uris()
        try:
            for uri in uris:
                if uri.startswith("file:/"):
                    continue
                f = Gio.File.new_for_uri(uri)
                f.mount_enclosing_volume(Gio.MountMountFlags.NONE,
                                         None,
                                         None,
                                         None)
        except Exception as e:
            Logger.error("Application::init(): %s" % e)

        cssProviderFile = Gio.File.new_for_uri(
            "resource:///org/gnome/Lollypop/application.css")
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.db = Database()
        self.cache = CacheDatabase()
        self.playlists = Playlists()
        self.albums = AlbumsDatabase(self.db)
        self.artists = ArtistsDatabase(self.db)
        self.genres = GenresDatabase(self.db)
        self.tracks = TracksDatabase(self.db)
        self.player = Player()
        self.inhibitor = Inhibitor()
        self.scanner = CollectionScanner()
        self.notify = NotificationManager()
        self.task_helper = TaskHelper()
        self.art_helper = ArtHelper()
        self.art = Art()
        self.art.update_art_size()
        self.ws_director = DirectorWebService()
        self.ws_director.start()
        if not self.settings.get_value("disable-mpris"):
            from lollypop.mpris import MPRIS
            MPRIS(self)

        settings = Gtk.Settings.get_default()
        self.__gtk_dark = settings.get_property(
            "gtk-application-prefer-dark-theme")
        if not self.__gtk_dark:
            dark = self.settings.get_value("dark-ui")
            settings.set_property("gtk-application-prefer-dark-theme", dark)
        ApplicationActions.__init__(self)
        monitor = Gio.NetworkMonitor.get_default()
        if monitor.get_network_available() and\
                not monitor.get_network_metered() and\
                self.settings.get_value("recent-youtube-dl"):
            self.task_helper.run(install_youtube_dl)

    def do_startup(self):
        """
            Init application
        """
        Gtk.Application.do_startup(self)
        Handy.init()
        if self.__window is None:
            from lollypop.window import Window
            self.init()
            self.__window = Window()
            self.__window.connect("delete-event", self.__hide_on_delete)
            self.__window.setup()
            self.__window.show()
            self.player.restore_state()

    def quit(self, vacuum=False):
        """
            Quit Lollypop
            @param vacuum as bool
        """
        self.__window.container.stop()
        self.__window.hide()
        if not self.ws_director.stop():
            GLib.timeout_add(100, self.quit, vacuum)
            return
        if self.settings.get_value("save-state"):
            self.__window.container.stack.save_history()
        # Then vacuum db
        if vacuum:
            self.__vacuum()
            self.art.clean_artwork()
        Gio.Application.quit(self)
        if GLib.environ_getenv(GLib.get_environ(), "DEBUG_LEAK") is not None:
            import gc
            gc.collect()
            for x in gc.garbage:
                s = str(x)
                print(type(x), "\n  ", s)

    def fullscreen(self):
        """
            Go fullscreen
        """
        def on_destroy(window):
            self.__fs_window = None
            self.__window.show()

        if self.__fs_window is None:
            from lollypop.fullscreen import FullScreen
            self.__fs_window = FullScreen()
            self.__fs_window.delayed_init()
            self.__fs_window.show()
            self.__fs_window.connect("destroy", on_destroy)
            self.__window.hide()
        else:
            self.__fs_window.destroy()

    @property
    def proxy_host(self):
        """
            Get proxy host
            @return str
        """
        return self.__proxy_host

    @property
    def proxy_port(self):
        """
            Get proxy port
            @return int
        """
        return self.__proxy_port

    @property
    def devices(self):
        """
            Get available devices
            Merge connected and known
            @return [str]
        """
        devices = self.__window.toolbar.end.devices_popover.devices
        devices += list(self.settings.get_value("devices"))
        result = []
        # Do not use set() + filter() because we want to keep order
        for device in devices:
            if device not in result and device != "":
                result.append(device)
        return result

    @property
    def is_fullscreen(self):
        """
            Return True if application is fullscreen
        """
        return self.__fs_window is not None

    @property
    def main_window(self):
        """
            Get main window
        """
        return self.__window

    @property
    def window(self):
        """
            Get current application window
            @return Gtk.Window
        """
        if self.__fs_window is not None:
            return self.__fs_window
        else:
            return self.__window

    @property
    def data_dir(self):
        """
            Get data dir
            @return str
        """
        return self.__data_dir

    @property
    def gtk_application_prefer_dark_theme(self):
        """
            Return default gtk value
            @return bool
        """
        return self.__gtk_dark

    @property
    def version(self):
        """
            Get Lollypop version
            @return srt
        """
        return self.__version

#######################
# PRIVATE             #
#######################
    def __save_state(self):
        """
            Save player state
        """
        if self.settings.get_value("save-state"):
            if self.player.current_track.id is None or\
                    self.player.current_track.storage_type &\
                    StorageType.EPHEMERAL:
                track_id = None
            else:
                track_id = self.player.current_track.id
                # Save albums context
                try:
                    with open(LOLLYPOP_DATA_PATH + "/Albums.bin", "wb") as f:
                        dump(self.player.albums, f)
                except Exception as e:
                    Logger.error("Application::__save_state(): %s" % e)
            dump(track_id, open(LOLLYPOP_DATA_PATH + "/track_id.bin", "wb"))
            dump([self.player.is_playing, self.player.is_party],
                 open(LOLLYPOP_DATA_PATH + "/player.bin", "wb"))
            dump(self.player.queue,
                 open(LOLLYPOP_DATA_PATH + "/queue.bin", "wb"))
            if self.player.current_track.id is not None:
                position = self.player.position
            else:
                position = 0
            dump(position, open(LOLLYPOP_DATA_PATH + "/position.bin", "wb"))
        self.player.stop_all()

    def __vacuum(self):
        """
            VACUUM DB
        """
        try:
            if self.scanner.is_locked():
                self.scanner.stop()
                GLib.idle_add(self.__vacuum)
                return
            SqlCursor.add(self.db)
            self.tracks.del_non_persistent(False)
            self.tracks.clean(False)
            self.albums.clean(False)
            self.artists.clean(False)
            self.genres.clean(False)
            SqlCursor.remove(self.db)
            self.cache.clean(True)

            with SqlCursor(self.db) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
            with SqlCursor(self.playlists) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
        except Exception as e:
            Logger.error("Application::__vacuum(): %s" % e)

    def __parse_uris(self, playlist_uris, audio_uris):
        """
            Parse playlist uris
            @param playlist_uris as [str]
            @param audio_uris as [str]
        """
        from gi.repository import TotemPlParser
        playlist_uri = playlist_uris.pop(0)
        parser = TotemPlParser.Parser.new()
        parser.connect("entry-parsed",
                       self.__on_entry_parsed,
                       audio_uris)
        parser.parse_async(playlist_uri, True, None,
                           self.__on_parse_finished,
                           playlist_uris, audio_uris)

    def __on_handle_local_options(self, app, options):
        """
            Handle local options
            @param app as Gio.Application
            @param options as GLib.VariantDict
        """
        if options.contains("version"):
            print("Lollypop %s" % self.__version)
            exit(0)
        return -1

    def __on_command_line(self, app, app_cmd_line):
        """
            Handle command line
            @param app as Gio.Application
            @param options as Gio.ApplicationCommandLine
        """
        try:
            args = app_cmd_line.get_arguments()
            options = app_cmd_line.get_options_dict()
            if options.contains("debug"):
                self.debug = True
            if options.contains("set-rating"):
                value = options.lookup_value("set-rating").get_string()
                try:
                    value = min(max(0, int(value)), 5)
                    if self.player.current_track.id is not None:
                        self.player.current_track.set_rate(value)
                except Exception as e:
                    Logger.error("Application::__on_command_line(): %s", e)
                    pass
            elif options.contains("play-pause"):
                self.player.play_pause()
            elif options.contains("stop"):
                self.player.stop()
            elif options.contains("play-ids"):
                try:
                    value = options.lookup_value("play-ids").get_string()
                    ids = value.split(";")
                    albums = []
                    for id in ids:
                        if id[0:2] == "a:":
                            album = Album(int(id[2:]))
                            self.player.add_album(album)
                            albums.append(album)
                        else:
                            track = Track(int(id[2:]))
                            self.player.add_album(track.album)
                            albums.append(track.album)
                    if albums and albums[0].tracks:
                        self.player.load(albums[0].tracks[0])
                except Exception as e:
                    Logger.error("Application::__on_command_line(): %s", e)
                    pass
            elif options.contains("next"):
                self.player.next()
            elif options.contains("prev"):
                self.player.prev()
            elif options.contains("emulate-phone"):
                self.__window.toolbar.end.devices_popover.add_fake_phone()
            elif len(args) > 1:
                audio_uris = []
                playlist_uris = []
                for uri in args[1:]:
                    parsed = urlparse(uri)
                    if parsed.scheme not in ["http", "https"]:
                        try:
                            uri = GLib.filename_to_uri(uri)
                        except:
                            pass
                        f = Gio.File.new_for_uri(uri)
                        # Try ./filename
                        if not f.query_exists():
                            uri = GLib.filename_to_uri(
                                "%s/%s" % (GLib.get_current_dir(), uri))
                            print(uri)
                            f = Gio.File.new_for_uri(uri)
                    file_type = get_file_type(uri)
                    if file_type == FileType.PLS:
                        playlist_uris.append(uri)
                    else:
                        audio_uris.append(uri)
                if playlist_uris:
                    self.__parse_uris(playlist_uris, audio_uris)
                else:
                    self.__on_parse_finished(None, None, [], audio_uris)
            elif self.__window is not None:
                if not self.__window.is_visible():
                    self.__window.present()
                    emit_signal(self.player, "status-changed")
                    emit_signal(self.player, "current-changed")
            Gdk.notify_startup_complete()
        except Exception as e:
            Logger.error("Application::__on_command_line(): %s", e)
        return 0

    def __on_parse_finished(self, source, result, playlist_uris, audio_uris):
        """
            Play stream
            @param source as None
            @param result as Gio.AsyncResult
            @param uris as ([str], [str])
        """
        if playlist_uris:
            self.__parse_uris(playlist_uris, audio_uris)
        else:
            self.scanner.update(ScanType.EXTERNAL, audio_uris)

    def __on_entry_parsed(self, parser, uri, metadata, audio_uris):
        """
            Add playlist entry to external files
            @param parser as TotemPlParser.Parser
            @param uri as str
            @param metadata as GLib.HastTable
            @param audio_uris as str
        """
        audio_uris.append(uri)

    def __hide_on_delete(self, widget, event):
        """
            Hide window
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        # Quit if background mode is on but player is off
        if not self.settings.get_value("background-mode") or\
                not self.player.is_playing:
            GLib.idle_add(self.quit, True)
        return widget.hide_on_delete()

    def __on_activate(self, application):
        """
            Call default handler
            @param application as Gio.Application
        """
        self.__window.present()
