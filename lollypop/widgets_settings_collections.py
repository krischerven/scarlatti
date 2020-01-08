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

from gi.repository import Gtk, GLib

from gettext import ngettext as ngettext

from lollypop.define import App, ScanType
from lollypop.database_history import History
from lollypop.database import Database
from lollypop.logger import Logger


class ChooserWidget(Gtk.FlowBoxChild):
    """
        Widget used to let user select a collection folder
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.FlowBoxChild.__init__(self)
        self.__action = None
        grid = Gtk.Grid()
        grid.set_property("orientation", Gtk.Orientation.HORIZONTAL)
        grid.show()
        self.__chooser_btn = Gtk.FileChooserButton()
        self.__chooser_btn.set_local_only(False)
        self.__chooser_btn.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.__chooser_btn.set_property("margin", 5)
        self.__chooser_btn.show()
        for child in self.__chooser_btn.get_children():
            if isinstance(child, Gtk.ComboBox):
                child.connect("scroll-event", self.__on_scroll_event)
                break
        grid.add(self.__chooser_btn)
        self.__action_btn = Gtk.Button()
        self.__action_btn.set_property("margin", 5)
        self.__action_btn.show()
        grid.add(self.__action_btn)
        self.__action_btn.connect("clicked", self.___do_action)
        self.show()
        self.add(grid)

    def set_dir(self, uri):
        """
            Set current selected uri for chooser
            @param uri as string
        """
        if uri:
            self.__chooser_btn.set_uri(uri)

    def set_icon(self, image):
        """
            Set image for action button
            @param image as Gtk.Image
        """
        self.__action_btn.set_image(image)

    def set_action(self, action):
        """
            Set action callback for button clicked signal
            @param action
        """
        self.__action = action

    def get_dir(self):
        """
            Return select directory uri
            @return uri as string
        """
        return self.__chooser_btn.get_uri()

#######################
# PRIVATE             #
#######################
    def __on_scroll_event(self, widget, event):
        """
            Block scroll event on combobox
            @param widget as Gtk.ComboBox
            @param event as Gdk.ScrollEvent
        """
        return True

    def ___do_action(self, widget):
        """
            If action defined, execute, else, remove widget
        """
        if self.__action:
            self.__action()
        else:
            self.destroy()


class CollectionsSettingsWidget(Gtk.Bin):
    """
        Widget allowing user to set collections
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        dirs = []
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsCollections.ui")
        self.__flowbox = builder.get_object("flowbox")
        self.__progress = builder.get_object("progress")
        self.__infobar = builder.get_object("infobar")
        self.__reset_button = builder.get_object("reset_button")

        if App().scanner.is_locked():
            builder.get_object("reset_button").set_sensitive(False)
        artists = App().artists.count()
        albums = App().albums.count()
        tracks = App().tracks.count()
        builder.get_object("artists").set_text(
            ngettext("%d artist", "%d artists", artists) % artists)
        builder.get_object("albums").set_text(
            ngettext("%d album", "%d albums", albums) % albums)
        builder.get_object("tracks").set_text(
            ngettext("%d track", "%d tracks", tracks) % tracks)

        for directory in App().settings.get_value("music-uris"):
            dirs.append(directory)

        # Main chooser
        self.__main_chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-add-symbolic",
                                             Gtk.IconSize.MENU)
        self.__main_chooser.set_icon(image)
        self.__main_chooser.set_action(self.__add_chooser)
        self.__flowbox.add(self.__main_chooser)
        if len(dirs) > 0:
            uri = dirs.pop(0)
        else:
            filename = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            if filename:
                uri = GLib.filename_to_uri(filename)
            else:
                uri = "/opt"

        self.__main_chooser.set_dir(uri)

        # Others choosers
        for directory in dirs:
            self.__add_chooser(directory)
        self.add(builder.get_object("widget"))
        builder.connect_signals(self)
        self.connect("destroy", self.__on_destroy)

#######################
# PROTECTED           #
#######################
    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            infobar.hide()

    def _on_confirm_button_clicked(self, button):
        """
            Reset database
            @param button as Gtk.Button
        """
        try:
            App().player.stop(True)
            App().cursors = {}
            uris = App().tracks.get_uris()
            self.__progress.show()
            history = History()
            self.__reset_button.get_toplevel().set_deletable(False)
            self.__reset_button.set_sensitive(False)
            self.__infobar.hide()
            self.__reset_database(uris, len(uris), history)
        except Exception as e:
            Logger.error("SettingsDialog::_on_confirm_button_clicked(): %s" %
                         e)

    def _on_reset_button_clicked(self, widget):
        """
            Show infobar
            @param widget as Gtk.Widget
        """
        self.__infobar.show()
        # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
        self.__infobar.queue_resize()

#######################
# PRIVATE             #
#######################
    def __add_chooser(self, directory=None):
        """
            Add a new chooser widget
            @param directory uri as string
        """
        chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-remove-symbolic",
                                             Gtk.IconSize.MENU)
        chooser.set_icon(image)
        if directory is not None:
            chooser.set_dir(directory)
        self.__flowbox.add(chooser)

    def __reset_database(self, uris, count, history):
        """
            Backup database and reset
            @param uris as [str]
            @param count as int
            @param history as History
        """
        if uris:
            App().stop_spotify()
            uri = uris.pop(0)
            App().scanner.del_from_db(uri, True)
            self.__progress.set_fraction((count - len(uris)) / count)
            GLib.idle_add(self.__reset_database, uris, count, history)
        else:
            self.__progress.hide()
            App().player.stop()
            App().db.drop_db()
            App().db = Database()
            App().window.container.go_home()
            App().scanner.update(ScanType.FULL)
            self.__progress.get_toplevel().set_deletable(True)

    def __on_destroy(self, widget):
        """
            Save settings and update if needed
            @param widget as Gtk.Window
        """
        # Music uris
        uris = []
        default = GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_MUSIC)
        if default is not None:
            default_uri = GLib.filename_to_uri(default)
        else:
            default_uri = None
        main_uri = self.__main_chooser.get_dir()
        choosers = self.__flowbox.get_children()
        if main_uri != default_uri or choosers:
            uris.append(main_uri)
            for chooser in choosers:
                uri = chooser.get_dir()
                if uri is not None and uri not in uris:
                    uris.append(uri)

        previous = App().settings.get_value("music-uris")
        App().settings.set_value("music-uris", GLib.Variant("as", uris))

        if set(previous) != set(uris):
            to_delete = [uri for uri in previous if uri not in uris]
            if to_delete:
                # We need to do a full scan
                App().scanner.update(ScanType.FULL)
            else:
                # Only scan new folders
                to_scan = [uri for uri in uris if uri not in previous]
                if to_scan:
                    App().scanner.update(ScanType.NEW_FILES, to_scan)
