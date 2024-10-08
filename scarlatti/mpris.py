# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2016 Gaurav Narula
# Copyright (c) 2016 Felipe Borges <felipeborges@gnome.org>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
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

from gi.repository import Gio, Gst, GLib, Gtk

from random import randint

from scarlatti.logger import Logger
from scarlatti.define import App, ArtSize, Repeat, Notifications
from scarlatti.objects_track import Track


class Server:

    def __init__(self, con, path):
        method_outargs = {}
        method_inargs = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = "(" + "".join(
                              [arg.signature for arg in method.out_args]) + ")"
                method_inargs[method.name] = tuple(
                    arg.signature for arg in method.in_args)

            con.register_object(path,
                                interface,
                                self.on_method_call,
                                None,
                                None)

        self.method_inargs = method_inargs
        self.method_outargs = method_outargs

    def on_method_call(self,
                       connection,
                       sender,
                       object_path,
                       interface_name,
                       method_name,
                       parameters,
                       invocation):

        args = list(parameters.unpack())
        for i, sig in enumerate(self.method_inargs[method_name]):
            if sig == "h":
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        try:
            result = getattr(self, method_name)(*args)

            # out_args is atleast (signature1).
            # We therefore always wrap the result as a tuple.
            # Refer to https://bugzilla.gnome.org/show_bug.cgi?id=765603
            result = (result,)

            out_args = self.method_outargs[method_name]
            if out_args != "()":
                variant = GLib.Variant(out_args, result)
                invocation.return_value(variant)
            else:
                invocation.return_value(None)
        except:
            pass


class MPRIS(Server):
    """
    <!DOCTYPE node PUBLIC
    "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
    "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
    <node>
        <interface name="org.freedesktop.DBus.Introspectable">
            <method name="Introspect">
                <arg name="data" direction="out" type="s"/>
            </method>
        </interface>
        <interface name="org.freedesktop.DBus.Properties">
            <method name="Get">
                <arg name="interface" direction="in" type="s"/>
                <arg name="property" direction="in" type="s"/>
                <arg name="value" direction="out" type="v"/>
            </method>
            <method name="Set">
                <arg name="interface_name" direction="in" type="s"/>
                <arg name="property_name" direction="in" type="s"/>
                <arg name="value" direction="in" type="v"/>
            </method>
            <method name="GetAll">
                <arg name="interface" direction="in" type="s"/>
                <arg name="properties" direction="out" type="a{sv}"/>
            </method>
        </interface>
        <interface name="org.mpris.MediaPlayer2">
            <method name="Raise">
            </method>
            <method name="Quit">
            </method>
            <property name="CanQuit" type="b" access="read" />
            <property name="Fullscreen" type="b" access="readwrite" />
            <property name="CanRaise" type="b" access="read" />
            <property name="HasTrackList" type="b" access="read"/>
            <property name="Identity" type="s" access="read"/>
            <property name="DesktopEntry" type="s" access="read"/>
            <property name="SupportedUriSchemes" type="as" access="read"/>
            <property name="SupportedMimeTypes" type="as" access="read"/>
        </interface>
        <interface name="org.mpris.MediaPlayer2.Player">
            <method name="Next"/>
            <method name="Previous"/>
            <method name="Pause"/>
            <method name="PlayPause"/>
            <method name="Stop"/>
            <method name="Play"/>
            <method name="Seek">
                <arg direction="in" name="Offset" type="x"/>
            </method>
            <method name="SetPosition">
                <arg direction="in" name="TrackId" type="o"/>
                <arg direction="in" name="Position" type="x"/>
            </method>
            <method name="OpenUri">
                <arg direction="in" name="Uri" type="s"/>
            </method>
            <signal name="Seeked">
                <arg name="Position" type="x"/>
            </signal>
            <property name="PlaybackStatus" type="s" access="read"/>
            <property name="LoopStatus" type="s" access="readwrite"/>
            <property name="Rate" type="d" access="readwrite"/>
            <property name="Shuffle" type="b" access="readwrite"/>
            <property name="Metadata" type="a{sv}" access="read">
            </property>
            <property name="Volume" type="d" access="readwrite"/>
            <property name="Position" type="x" access="read"/>
            <property name="MinimumRate" type="d" access="read"/>
            <property name="MaximumRate" type="d" access="read"/>
            <property name="CanGoNext" type="b" access="read"/>
            <property name="CanGoPrevious" type="b" access="read"/>
            <property name="CanPlay" type="b" access="read"/>
            <property name="CanPause" type="b" access="read"/>
            <property name="CanSeek" type="b" access="read"/>
            <property name="CanControl" type="b" access="read"/>
        </interface>
        <interface name="org.mpris.MediaPlayer2.ExtensionSetRatings">
            <method name="SetRating">\
                <arg direction="in" name="TrackId" type="o"/>
                <arg direction="in" name="Rating" type="d"/>\
            </method>\
            <property name="HasRatingsExtension" type="b" access="read"/>\
        </interface>
    </node>
    """
    __MPRIS_IFACE = "org.mpris.MediaPlayer2"
    __MPRIS_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
    __MPRIS_RATINGS_IFACE = "org.mpris.MediaPlayer2.ExtensionSetRatings"
    __MPRIS_SCARLATTI = "org.mpris.MediaPlayer2.Scarlatti"
    __MPRIS_PATH = "/org/mpris/MediaPlayer2"

    def __init__(self, app):
        self.__app = app
        self.__rating = None
        self.__scarlatti_id = 0
        self.__metadata = {"mpris:trackid": GLib.Variant(
            "o",
            "/org/mpris/MediaPlayer2/TrackList/NoTrack")}
        self.__track_id = self.__get_media_id(0)
        self.__bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        Gio.bus_own_name_on_connection(self.__bus,
                                       self.__MPRIS_SCARLATTI,
                                       Gio.BusNameOwnerFlags.NONE,
                                       None,
                                       None)
        Server.__init__(self, self.__bus, self.__MPRIS_PATH)
        App().player.connect("current-changed", self.__on_current_changed)
        App().player.connect("seeked", self.__on_seeked)
        App().player.connect("status-changed", self.__on_status_changed)
        App().player.connect("volume-changed", self.__on_volume_changed)
        App().player.connect("rate-changed", self.__on_rate_changed)
        App().settings.connect("changed::shuffle", self.__on_shuffle_changed)
        App().settings.connect("changed::repeat", self.__on_repeat_changed)

    def Raise(self):
        self.__app.window.present_with_time(Gtk.get_current_event_time())

    def Quit(self):
        self.__app.quit()

    def Next(self):
        App().player.next()
        if App().settings.get_enum("notifications") == Notifications.MPRIS:
            App().notify.send_track(App().player.current_track)

    def Previous(self):
        App().player.prev()
        if App().settings.get_enum("notifications") == Notifications.MPRIS:
            App().notify.send_track(App().player.current_track)

    def Pause(self):
        App().player.pause()

    def PlayPause(self):
        App().player.play_pause()

    def Stop(self):
        App().player.stop()

    def Play(self):
        if App().player.current_track.id is None:
            App().player.set_party(True)
        else:
            App().player.play()

    def SetPosition(self, track_id, position):
        App().player.seek(position / 1000)

    def OpenUri(self, uri):
        track_id = App().tracks.get_id_by_uri(uri)
        if track_id:
            App().player.load(Track(track_id))

    def Seek(self, offset):
        position = App().player.position
        App().player.seek(position + offset / 1000)

    def Seeked(self, position):
        self.__bus.emit_signal(
            None,
            self.__MPRIS_PATH,
            self.__MPRIS_PLAYER_IFACE,
            "Seeked",
            GLib.Variant.new_tuple(GLib.Variant("x", position)))

    def SetRating(self, track_id, rating):
        # We don't currently care about the trackId since
        # we have not yet implemented the TrackList interface.
        App().player.current_track.set_rate(int(rating * 5))

    def Get(self, interface, property_name):
        if property_name in ["CanQuit", "CanRaise", "CanSeek",
                             "CanControl", "HasRatingsExtension"]:
            return GLib.Variant("b", True)
        elif property_name == "HasTrackList":
            return GLib.Variant("b", False)
        elif property_name == "Shuffle":
            return App().settings.get_value("shuffle")
        elif property_name in ["Rate", "MinimumRate", "MaximumRate"]:
            return GLib.Variant("d", 1.0)
        elif property_name == "Identity":
            return GLib.Variant("s", "Scarlatti")
        elif property_name == "DesktopEntry":
            return GLib.Variant("s", "org.scarlatti.Scarlatti")
        elif property_name == "SupportedUriSchemes":
            return GLib.Variant("as", ["file", "http"])
        elif property_name == "SupportedMimeTypes":
            return GLib.Variant("as", ["application/ogg",
                                       "audio/x-vorbis+ogg",
                                       "audio/x-flac",
                                       "audio/mpeg"])
        elif property_name == "PlaybackStatus":
            return GLib.Variant("s", self.__get_status())
        elif property_name == "LoopStatus":
            repeat = App().settings.get_enum("repeat")
            if repeat == Repeat.ALL:
                value = "Playlist"
            elif repeat == Repeat.TRACK:
                value = "Track"
            else:
                value = "None"
            return GLib.Variant("s", value)
        elif property_name == "Metadata":
            return GLib.Variant("a{sv}", self.__metadata)
        elif property_name == "Volume":
            return GLib.Variant("d", App().player.volume)
        elif property_name == "Position":
            return GLib.Variant(
                "x",
                App().player.position * 1000)
        elif property_name in ["CanGoNext", "CanGoPrevious",
                               "CanPlay", "CanPause"]:
            return GLib.Variant("b", App().player.current_track.id is not None)

    def GetAll(self, interface):
        ret = {}
        if interface == self.__MPRIS_IFACE:
            for property_name in ["CanQuit",
                                  "CanRaise",
                                  "HasTrackList",
                                  "Identity",
                                  "DesktopEntry",
                                  "SupportedUriSchemes",
                                  "SupportedMimeTypes"]:
                ret[property_name] = self.Get(interface, property_name)
        elif interface == self.__MPRIS_PLAYER_IFACE:
            for property_name in ["PlaybackStatus",
                                  "LoopStatus",
                                  "Rate",
                                  "Shuffle",
                                  "Metadata",
                                  "Volume",
                                  "Position",
                                  "MinimumRate",
                                  "MaximumRate",
                                  "CanGoNext",
                                  "CanGoPrevious",
                                  "CanPlay",
                                  "CanPause",
                                  "CanSeek",
                                  "CanControl"]:
                ret[property_name] = self.Get(interface, property_name)
        elif interface == self.__MPRIS_RATINGS_IFACE:
            ret["HasRatingsExtension"] = GLib.Variant("b", True)
        return ret

    def Set(self, interface, property_name, new_value):
        if property_name == "Volume":
            App().player.set_volume(new_value)
        elif property_name == "Shuffle":
            App().settings.set_value("shuffle", GLib.Variant("b", new_value))
        elif property_name == "LoopStatus":
            if new_value == "Playlist":
                value = Repeat.ALL
            elif new_value == "Track":
                value = Repeat.TRACK
            else:
                value = Repeat.NONE
            App().settings.set_enum("repeat", value)

    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        self.__bus.emit_signal(None,
                               self.__MPRIS_PATH,
                               "org.freedesktop.DBus.Properties",
                               "PropertiesChanged",
                               GLib.Variant.new_tuple(
                                   GLib.Variant("s", interface_name),
                                   GLib.Variant("a{sv}", changed_properties),
                                   GLib.Variant("as", invalidated_properties)))

    def Introspect(self):
        return self.__doc__

#######################
# PRIVATE             #
#######################

    def __get_media_id(self, track_id):
        """
            TrackId's must be unique even up to
            the point that if you repeat a song
            it must have a different TrackId.
        """
        track_id = track_id + randint(10000000, 90000000)
        return GLib.Variant("o", "/org/scarlatti/Scarlatti/TrackId/%s" % track_id)

    def __get_status(self):
        state = App().player.get_status()
        if state == Gst.State.PLAYING:
            return "Playing"
        elif state == Gst.State.PAUSED:
            return "Paused"
        else:
            return "Stopped"

    def __update_metadata(self):
        self.__metadata = {}
        if App().player.current_track.id is None or\
                self.__get_status() == "Stopped":
            self.__metadata = {"mpris:trackid": GLib.Variant(
                "o",
                "/org/mpris/MediaPlayer2/TrackList/NoTrack")}
        else:
            self.__metadata["mpris:trackid"] = self.__track_id
            track_number = App().player.current_track.number
            if track_number is None:
                track_number = 1
            self.__metadata["xesam:trackNumber"] = GLib.Variant(
                "i",
                track_number)
            self.__metadata["xesam:title"] = GLib.Variant(
                "s",
                App().player.current_track.name)
            self.__metadata["xesam:album"] = GLib.Variant(
                "s",
                App().player.current_track.album.name)
            self.__metadata["xesam:artist"] = GLib.Variant(
                "as",
                App().player.current_track.artists)
            self.__metadata["xesam:albumArtist"] = GLib.Variant(
                "as",
                App().player.current_track.album_artists)
            self.__metadata["mpris:length"] = GLib.Variant(
                "x",
                App().player.current_track.duration * 1000)
            self.__metadata["xesam:genre"] = GLib.Variant(
                "as",
                App().player.current_track.genres)
            self.__metadata["xesam:url"] = GLib.Variant(
                "s",
                App().player.current_track.uri)
            self.__metadata["xesam:userRating"] = GLib.Variant(
                "d",
                App().player.current_track.rate / 5)
            cover_path = App().album_art.get_cache_path(
                    App().player.current_track.album,
                    ArtSize.MPRIS, ArtSize.MPRIS)
            if cover_path is not None:
                self.__metadata["mpris:artUrl"] = GLib.Variant(
                    "s",
                    "file://" + cover_path)

    def __on_seeked(self, player, position):
        self.Seeked(position * 1000)

    def __on_volume_changed(self, player, data=None):
        self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE,
                               {"Volume": GLib.Variant("d",
                                                       App().player.volume), },
                               [])

    def __on_shuffle_changed(self, settings, value):
        properties = {"Shuffle": App().settings.get_value("shuffle")}
        self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])

    def __on_repeat_changed(self, settings, value):
        repeat = App().settings.get_enum("repeat")
        if repeat == Repeat.ALL:
            value = "Playlist"
        elif repeat == Repeat.TRACK:
            value = "Track"
        else:
            value = "None"
        properties = {"LoopStatus": GLib.Variant("s", value)}
        self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])

    def __on_rate_changed(self, player, rated_track_id, rating):
        # We only care about the current Track's rating.
        if rated_track_id == self.__scarlatti_id:
            self.__rating = rating
            self.__update_metadata()
            properties = {"Metadata": GLib.Variant("a{sv}", self.__metadata)}
            self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])

    def __on_current_changed(self, player):
        if App().player.current_track.id is None:
            self.__scarlatti_id = 0
        else:
            self.__scarlatti_id = App().player.current_track.id
        # We only need to recalculate a new trackId at song changes.
        self.__track_id = self.__get_media_id(self.__scarlatti_id)
        self.__rating = None
        self.__update_metadata()
        properties = {"Metadata": GLib.Variant("a{sv}", self.__metadata),
                      "CanPlay": GLib.Variant("b", True),
                      "CanPause": GLib.Variant("b", True),
                      "CanGoNext": GLib.Variant("b", True),
                      "CanGoPrevious": GLib.Variant("b", True)}
        try:
            self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])
        except Exception as e:
            Logger.error("MPRIS::__on_current_changed(): %s" % e)

    def __on_status_changed(self, data=None):
        properties = {"PlaybackStatus": GLib.Variant("s", self.__get_status())}
        self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])
