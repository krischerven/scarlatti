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

from gi.repository import Gtk, GLib, Gio, Pango

from gettext import gettext as _

from lollypop.view import View
from lollypop.objects_radio import Radio
from lollypop.define import App, Sizing, ArtBehaviour
from lollypop.controller_information import InformationController
from lollypop.utils import escape, get_network_available
from lollypop.logger import Logger
from lollypop.helper_task import TaskHelper
from lollypop.helper_lyrics import SyncLyricsHelper


class LyricsLabel(Gtk.Stack):
    """
        Lyrics label with effect on change
    """

    def __init__(self):
        """
            Init label
        """
        Gtk.Stack.__init__(self)
        self.__label1 = Gtk.Label.new()
        self.__label1.set_line_wrap_mode(Pango.WrapMode.WORD)
        self.__label1.set_line_wrap(True)
        self.__label1.set_justify(Gtk.Justification.CENTER)
        self.__label2 = Gtk.Label.new()
        self.__label2.set_line_wrap_mode(Pango.WrapMode.WORD)
        self.__label2.set_line_wrap(True)
        self.__label2.set_justify(Gtk.Justification.CENTER)
        self.__label1.show()
        self.__label2.show()
        self.add(self.__label1)
        self.add(self.__label2)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.set_transition_duration(200)

    def set_text(self, text):
        """
            Set label text
            @param text as str
        """
        self.next()
        self.get_visible_child().set_text(text)

    def set_markup(self, markup):
        """
            Set label markup
            @param markup as str
        """
        self.next()
        self.get_visible_child().set_markup(markup)

    def next(self):
        """
            Show next label
        """
        for child in self.get_children():
            if child != self.get_visible_child():
                self.set_visible_child(child)
                break


class LyricsView(View, InformationController):
    """
        Show lyrics for track
    """

    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        InformationController.__init__(self, False,
                                       ArtBehaviour.BLUR_MAX |
                                       ArtBehaviour.CROP |
                                       ArtBehaviour.DARKER)
        self.__current_changed_id = None
        self.__size_allocate_timeout_id = None
        self.__lyrics_timeout_id = None
        self.__downloads_running = 0
        self.__lyrics_text = ""
        self.__size = 0
        self.__cancellable = Gio.Cancellable()
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/LyricsView.ui")
        builder.connect_signals(self)
        self._artwork = builder.get_object("cover")
        self.__lyrics_label = LyricsLabel()
        self.__lyrics_label.show()
        builder.get_object("viewport").add(self.__lyrics_label)
        self.__translate_button = builder.get_object("translate_button")
        # We do not use View scrolled window because it does not work with
        # an overlay
        self.add(builder.get_object("widget"))
        self.connect("size-allocate", self.__on_size_allocate)
        self.__sync_lyrics_helper = SyncLyricsHelper()

    def populate(self, track):
        """
            Set lyrics
            @param track as Track
        """
        self.__current_track = track
        self.update_artwork(self.__size, self.__size)
        self.__lyrics_text = ""
        self.__lyrics_label.set_text(_("Loading…"))
        self.__cancellable.cancel()
        self.__cancellable = Gio.Cancellable()
        self.__sync_lyrics_helper.load(track)
        self.__update_lyrics_style()
        if self.__sync_lyrics_helper.available:
            self.__translate_button.hide()
            if self.__lyrics_timeout_id is None:
                self.__lyrics_timeout_id = GLib.timeout_add(
                    500, self.__show_sync_lyrics)
            return
        else:
            self.__translate_button.show()
            if self.__lyrics_timeout_id is not None:
                GLib.source_remove(self.__lyrics_timeout_id)
                self.__lyrics_timeout_id = None
        # First try to get lyrics from tags
        from lollypop.tagreader import TagReader
        reader = TagReader()
        try:
            info = reader.get_info(self.__current_track.uri)
        except:
            info = None
        if info is not None:
            tags = info.get_tags()
            self.__lyrics_text = reader.get_lyrics(tags)
        if self.__lyrics_text:
            self.__lyrics_label.set_text(self.__lyrics_text)
        else:
            if get_network_available("WIKIA"):
                self.__download_wikia_lyrics()
            if get_network_available("GENIUS"):
                self.__download_genius_lyrics()
            if self.__downloads_running == 0:
                self.__lyrics_label.set_text(
                    _("You have disabled lyrics search in network settings !"))

##############
# PROTECTED  #
##############
    def _on_translate_toggled(self, button):
        """
            Translate lyrics
            @param button as Gtk.Button
        """
        if button.get_active():
            App().task_helper.run(self.__get_blob, self.__lyrics_text,
                                  callback=(self.__lyrics_label.set_text,))
        else:
            self.__lyrics_label.set_text(self.__lyrics_text)

    def _on_map(self, widget):
        """
            Set active ids
            @param widget as Gtk.Widget
        """
        App().window.emit("can-go-back-changed", True)
        self.__current_changed_id = App().player.connect(
            "current-changed", self.__on_current_changed)

    def _on_unmap(self, widget):
        """
            Connect player signal
            @param widget as Gtk.Widget
        """
        if self.__lyrics_timeout_id is not None:
            GLib.source_remove(self.__lyrics_timeout_id)
            self.__lyrics_timeout_id = None
        if self.__current_changed_id is not None:
            App().player.disconnect(self.__current_changed_id)
            self.__current_changed_id = None

############
# PRIVATE  #
############
    def __show_sync_lyrics(self):
        """
            Show sync lyrics for track
        """
        timestamp = App().player.position / 1000000
        (previous, current, next) =\
            self.__sync_lyrics_helper.get_lyrics_for_timestamp(timestamp)
        lyrics = ""
        for line in previous:
            if line:
                escaped = GLib.markup_escape_text(line)
                lyrics += "<span alpha='20000'>%s</span>" % escaped + "\n"
        for line in current:
            escaped = GLib.markup_escape_text(line)
            lyrics += "<span>%s</span>" % escaped + "\n"
        for line in next:
            if line:
                escaped = GLib.markup_escape_text(line)
                lyrics += "<span alpha='20000'>%s</span>" % escaped + "\n"
        self.__lyrics_label.set_markup(lyrics)
        return True

    def __get_blob(self, text):
        """
            Translate text with current user locale
            @param text as str
        """
        try:
            locales = GLib.get_language_names()
            user_code = locales[0].split(".")[0]
            try:
                from textblob.blob import TextBlob
            except:
                return _("You need to install python3-textblob module")
            blob = TextBlob(text)
            return str(blob.translate(to=user_code))
        except Exception as e:
            Logger.error("LyricsView::__get_blob(): %s", e)
            return _("Can't translate this lyrics")

    def __download_wikia_lyrics(self):
        """
            Downloas lyrics from wikia
        """
        self.__downloads_running += 1
        # Update lyrics
        if isinstance(self.__current_track, Radio):
            split = self.__current_track.name.split(" - ")
            if len(split) < 2:
                return
            artist = GLib.uri_escape_string(
                split[0],
                None,
                False)
            title = GLib.uri_escape_string(
                split[1],
                None,
                False)
        else:
            if self.__current_track.artists:
                artist = GLib.uri_escape_string(
                    self.__current_track.artists[0],
                    None,
                    False)
            elif self.__current_track.album_artists:
                artist = self.__current_track.album_artists[0]
            else:
                artist = ""
            title = GLib.uri_escape_string(
                self.__current_track.name,
                None,
                False)
        uri = "https://lyrics.wikia.com/wiki/%s:%s" % (artist, title)
        helper = TaskHelper()
        helper.load_uri_content(uri,
                                self.__cancellable,
                                self.__on_lyrics_downloaded,
                                "lyricbox",
                                "\n")

    def __download_genius_lyrics(self):
        """
            Download lyrics from genius
        """
        self.__downloads_running += 1
        # Update lyrics
        if isinstance(self.__current_track, Radio):
            split = App().player.current_track.name.split(" - ")
            if len(split) < 2:
                return
            artist = split[0]
            title = split[1]
        else:
            if self.__current_track.artists:
                artist = self.__current_track.artists[0]
            elif self.__current_track.album_artists:
                artist = self.__current_track.album_artists[0]
            else:
                artist = ""
            title = self.__current_track.name
        string = escape("%s %s" % (artist, title))
        uri = "https://genius.com/%s-lyrics" % string.replace(" ", "-")
        helper = TaskHelper()
        helper.load_uri_content(uri,
                                self.__cancellable,
                                self.__on_lyrics_downloaded,
                                "song_body-lyrics",
                                "")

    def __update_lyrics_style(self):
        """
            Update lyrics style based on current view width
        """
        context = self.get_style_context()
        for cls in context.list_classes():
            context.remove_class(cls)
        context.add_class("lyrics")
        context.add_class("black")
        width = self.get_allocated_width()
        if width > Sizing.LARGE:
            if self.__sync_lyrics_helper.available:
                context.add_class("text-xx-large")
            else:
                context.add_class("text-x-large")
        elif width > Sizing.MONSTER:
            if self.__sync_lyrics_helper.available:
                context.add_class("text-x-large")
            else:
                context.add_class("text-large")
        elif width > Sizing.BIG:
            if self.__sync_lyrics_helper.available:
                context.add_class("text-large")
            else:
                context.add_class("text-medium")
        elif self.__sync_lyrics_helper.available:
            context.add_class("text-medium")

    def __handle_size_allocation(self):
        """
            Update style and resize cover
        """
        self.__size_allocate_timeout_id = None
        self.__update_lyrics_style()
        self._previous_artwork_id = None
        self.update_artwork(self.__size, self.__size)

    def __on_size_allocate(self, widget, allocation):
        """
            Update cover size
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        size = max(allocation.width, allocation.height)
        if size == self.__size:
            return
        self.__size = size
        if self.__size_allocate_timeout_id is not None:
            GLib.source_remove(self.__size_allocate_timeout_id)
        self.__size_allocate_timeout_id = GLib.idle_add(
            self.__handle_size_allocation)

    def __on_lyrics_downloaded(self, uri, status, data, cls, separator):
        """
            Show lyrics
            @param uri as str
            @param status as bool
            @param data as bytes
            @param cls as str
            @param separator as str
        """
        self.__downloads_running -= 1
        if self.__lyrics_text:
            return
        if status:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(data, 'html.parser')
                self.__lyrics_text = soup.find_all(
                    "div", class_=cls)[0].get_text(separator=separator)
                self.__lyrics_label.set_text(self.__lyrics_text)
            except Exception as e:
                Logger.warning("LyricsView::__on_lyrics_downloaded(): %s", e)
        if not self.__lyrics_text and self.__downloads_running == 0:
            self.__lyrics_label.set_text(_("No lyrics found ") + "😓")
            self.__translate_button.set_sensitive(False)

    def __on_current_changed(self, player):
        """
            Update lyrics
            @param player as Player
        """
        self.populate(App().player.current_track)
        self.__translate_button.set_sensitive(True)
