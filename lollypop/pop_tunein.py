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

from gi.repository import Gtk, GLib, Gio, GdkPixbuf, Gdk, Pango

from gettext import gettext as _

from lollypop.radios import Radios
from lollypop.logger import Logger
from lollypop.define import App, ArtSize
from lollypop.utils import get_network_available
from lollypop.list import LinkedList
from lollypop.objects import Track
from lollypop.helper_task import TaskHelper


class TuneItem:
    TEXT = ""
    URL = ""
    LOGO = ""


class TuneinPopover(Gtk.Popover):
    """
        Popover showing tunin radios
    """

    def __init__(self, radios=None):
        """
            Init Popover
            @param radios as Radios
        """
        Gtk.Popover.__init__(self)
        self.__cancellable = Gio.Cancellable()
        if radios is not None:
            self.__radios = radios
        else:
            self.__radios = Radios()
        self.__timeout_id = None
        self.__history = None
        self.__covers_to_download = []

        self.__stack = Gtk.Stack()
        self.__stack.set_property("expand", True)
        self.__stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/TuneinPopover.ui")
        builder.connect_signals(self)
        widget = builder.get_object("widget")
        widget.attach(self.__stack, 0, 2, 5, 1)

        self.__back_btn = builder.get_object("back_btn")
        self.__home_btn = builder.get_object("home_btn")
        self.__label = builder.get_object("label")

        self.__view = Gtk.FlowBox()
        self.__view.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__view.set_max_children_per_line(100)
        self.__view.set_property("row-spacing", 10)
        self.__view.set_property("expand", True)
        self.__view.show()

        self.__spinner = builder.get_object("spinner")

        builder.get_object("viewport").add(self.__view)
        builder.get_object("viewport").set_property("margin", 10)

        self.__scrolled = builder.get_object("scrolled")
        self.__stack.add_named(self.__spinner, "spinner")
        self.__stack.add_named(self.__label, "label")
        self.__stack.add_named(self.__scrolled, "scrolled")
        self.add(widget)
        self.connect("map", self.__on_map)
        self.connect("unmap", self.__on_unmap)

    def populate(self, uri="http://opml.radiotime.com/Browse.ashx?c="):
        """
            Populate view for uri
            @param uri as str
        """
        if not get_network_available("TUNEIN"):
            self.__show_message(_("Can't connect to TuneIn…"))
            return
        if self.__view.get_children():
            return
        self.__populate(uri)

#######################
# PROTECTED           #
#######################
    def _on_back_btn_clicked(self, btn):
        """
            Go to previous URL
            @param btn as Gtk.Button
        """
        if self.__history.prev is None:
            return
        self.__history = self.__history.prev
        self.__stack.set_visible_child_name("spinner")
        self.__spinner.start()
        self.__clear()
        self.__populate(self.__history.value)
        if self.__history.prev is None:
            self.__back_btn.set_sensitive(False)

    def _on_home_btn_clicked(self, btn):
        """
            Go to root URL
            @param btn as Gtk.Button
        """
        self.__history = None
        self.__populate()

    def _on_search_changed(self, widget):
        """
            Timeout filtering, call _really_do_filterting()
            after timeout
            @param widget as Gtk.TextEntry
        """
        self.__history = None
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None

        text = widget.get_text()
        if text != "":
            self.__home_btn.set_sensitive(True)
            self.__timeout_id = GLib.timeout_add(1000,
                                                 self.__on_search_timeout,
                                                 text)
        else:
            self.__history = None
            self.__populate()

#######################
# PRIVATE             #
#######################
    def __populate(self, uri="http://opml.radiotime.com/Browse.ashx?c="):
        """
            Populate view for uri
            @param uri as str
        """
        self.__clear()
        self.__cancellable = Gio.Cancellable()
        self.__spinner.start()
        self.__stack.set_visible_child_name("spinner")
        self.__back_btn.set_sensitive(False)
        self.__home_btn.set_sensitive(False)
        self.__label.set_text(_("Please wait…"))
        helper = TaskHelper()
        helper.load_uri_content(uri,
                                self.__cancellable,
                                self.__on_uri_content)

    def __show_message(self, message=""):
        """
            Show not found message
            @param message as str
        """
        # TODO Add a string
        self.__label.set_text(message)
        self.__stack.set_visible_child_name("label")
        self.__home_btn.set_sensitive(True)

    def __add_items(self, items):
        """
            Add current items
            @param items as [TuneItem]
            @thread safe
        """
        GLib.idle_add(self.__add_item, items)

    def __add_item(self, items):
        """
            Add item
            @param items as [TuneItem]
        """
        if items:
            item = items.pop(0)
            child = Gtk.Grid()
            child.set_column_spacing(5)
            child.set_property("halign", Gtk.Align.START)
            child.show()
            link = Gtk.LinkButton.new_with_label(item.URL, item.TEXT)
            # Hack
            link.get_children()[0].set_ellipsize(Pango.EllipsizeMode.END)
            link.connect("activate-link", self.__on_activate_link, item)
            link.show()
            if item.TYPE == "audio":
                link.set_tooltip_text(_("Play"))
                button = Gtk.Button.new_from_icon_name("list-add-symbolic",
                                                       Gtk.IconSize.MENU)
                button.connect("clicked", self.__on_button_clicked, item)
                button.set_relief(Gtk.ReliefStyle.NONE)
                button.set_property("valign", Gtk.Align.CENTER)
                # Translators: radio context
                button.set_tooltip_text(_("Add"))
                button.show()
                child.add(button)
                image = Gtk.Image.new()
                image.set_property("width-request", ArtSize.MEDIUM)
                image.set_property("height-request", ArtSize.MEDIUM)
                image.show()
                child.add(image)
                self.__covers_to_download.append((item, image))
            else:
                link.set_tooltip_text("")
            child.add(link)
            self.__view.add(child)
            if not self.__cancellable.is_cancelled():
                GLib.idle_add(self.__add_items, items)
        else:  # Download images
            self.__home_btn.set_sensitive(self.__history is not None)
            self.__download_images()
            return
        # Remove spinner if exist
        if self.__stack.get_visible_child_name() == "spinner":
            self.__stack.set_visible_child_name("scrolled")
            self.__spinner.stop()
            self.__label.set_text("")
            self.__home_btn.set_sensitive(self.__history is not None)

    def __download_images(self):
        """
            Download and set image for TuneItem
            @thread safe
        """
        if self.__covers_to_download and not self.__cancellable.is_cancelled():
            (item, image) = self.__covers_to_download.pop(0)
            helper = TaskHelper()
            helper.load_uri_content(item.LOGO, self.__cancellable,
                                    self.__on_image_downloaded, image)

    def __clear(self):
        """
            Clear view
        """
        self.__cancellable.cancel()
        for child in self.__view.get_children():
            self.__view.remove(child)
            child.destroy()

    def __add_radio(self, item):
        """
            Add selected radio
            @param item as TuneIn Item
        """
        # Get cover art
        try:
            helper = TaskHelper()
            helper.load_uri_content(item.LOGO,
                                    None,
                                    self.__on_logo_uri_content,
                                    item.TEXT)
        except Exception as e:
            Logger.error("TuneinPopover::__add_radio: %s" % e)
        # Tunein in embbed uri in ashx files, so get content if possible
        helper = TaskHelper()
        helper.load_uri_content(item.URL, self.__cancellable,
                                self.__on_item_content, item.TEXT)

    def __on_logo_uri_content(self, uri, status, content, name):
        """
            Save image
            @param uri as str
            @param status as bool
            @param content as bytes  # The image
            @param name as str
        """
        if status:
            App().art.add_radio_artwork(name, content)

    def __on_map(self, widget):
        """
            Resize and disable global shortcuts
            @param widget as Gtk.Widget
        """
        window_size = App().window.get_size()
        height = window_size[1]
        width = min(500, window_size[0])
        self.set_size_request(width, height * 0.7)

    def __on_unmap(self, widget):
        """
            Enable global shortcuts
            @param widget as Gtk.Widget
        """
        self.__cancellable.cancel()

    def __on_item_content(self, uri, status, content, name):
        """
            Add radio to manager
            @param uri as str
            @param status as bool
            @param content as bytes
            @param name as str
        """
        if status and content:
            uri = content.decode("utf-8").split("\n")[0]
        self.__radios.add(name.replace("/", "-"), uri)

    def __on_image_downloaded(self, uri, status, content, image):
        """
            Set downloaded image
            @param uri as str
            @param status as bool
            @param content as bytes
            @param image as Gtk.Image
        """
        if status:
            bytes = GLib.Bytes(content)
            stream = Gio.MemoryInputStream.new_from_bytes(bytes)
            if stream is not None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                    stream,
                    ArtSize.MEDIUM,
                    ArtSize.MEDIUM,
                    True,
                    None)
                stream.close()
                surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                               0,
                                                               None)
                image.set_from_surface(surface)
        self.__download_images()

    def __on_activate_link(self, link, item):
        """
            Open new uri or just play stream
            @param link as Gtk.LinkButton
            @param item as TuneIn Item
        """
        if item.TYPE == "link":
            self.__scrolled.get_vadjustment().set_value(0.0)
            self.__populate(item.URL)
        elif item.TYPE == "audio":
            if get_network_available("TUNEIN"):
                # Cache for toolbar
                App().task_helper.run(App().art.copy_uri_to_cache,
                                      item.LOGO, item.TEXT,
                                      App().window.toolbar.info.art_size,
                                      App().window.toolbar.info.art_size)
                # Cache for MPRIS
                App().task_helper.run(App().art.copy_uri_to_cache,
                                      item.LOGO, item.TEXT,
                                      ArtSize.MONSTER, ArtSize.MONSTER)
            track = Track()
            track.set_radio(item.TEXT, item.URL)
            App().player.load(track)
        return True

    def __on_uri_content(self, uri, status, content):
        """
            Extract content
            @param uri as str
            @param status as bool
            @param content as bytes
        """
        try:
            if status:
                if self.__history is not None:
                    self.__back_btn.set_sensitive(True)
                self.__history = LinkedList(uri, None, self.__history)
                if content:
                    import xml.etree.ElementTree as xml
                    items = []
                    root = xml.fromstring(content)
                    for child in root.iter("outline"):
                        try:
                            item = TuneItem()
                            item.URL = child.attrib["URL"]
                            item.TEXT = child.attrib["text"].replace("/", "-")
                            try:
                                item.LOGO = child.attrib["image"]
                            except:
                                pass
                            item.TYPE = child.attrib["type"]
                            items.append(item)
                        except:
                            del item
                    if items:
                        self.__add_items(items)
                    else:
                        self.__show_message(_("No result…"))
                else:
                    self.__show_message(_("No result…"))
            else:
                raise Exception(status)
        except Exception as e:
            Logger.error("TuneinPopover::__on_uri_content(): %s" % e)
            self.__show_message(_("Can't connect to TuneIn…"))

    def __on_button_clicked(self, button, item):
        """
            Play the radio
            @param link as Gtk.Button
            @param item as TuneIn Item
        """
        self.__timeout_id = None
        self.__add_radio(item)
        self.hide()

    def __on_search_timeout(self, string):
        """
            Populate widget
            @param string as str
        """
        self.__timeout_id = None
        uri = "http://opml.radiotime.com/Search.ashx?query=%s" %\
            GLib.uri_escape_string(string, "/", False)
        self.__populate(uri)
