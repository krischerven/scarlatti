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

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

from gettext import gettext as _

from lollypop.widgets_utils import Popover
from lollypop.logger import Logger
from lollypop.define import App, ArtSize, ArtBehaviour
from lollypop.helper_signals import SignalsHelper, signals


class ArtworkSearchChild(Gtk.FlowBoxChild):
    """
        Child for ArtworkSearch
    """

    def __init__(self, api=None):
        """
            Init child
            @param api as str
        """
        Gtk.FlowBoxChild.__init__(self)
        self.__bytes = None
        self.__api = api
        self.__image = Gtk.Image()
        self.__image.show()
        self.__label = Gtk.Label()
        self.__label.show()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        grid.show()
        grid.add(self.__image)
        grid.add(self.__label)
        grid.set_row_spacing(5)
        self.__image.get_style_context().add_class("cover-frame")
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self.add(grid)

    def populate(self, bytes):
        """
            Populate images with bytes
            @param bytes as bytes
            @return bool if success
        """
        try:
            scale_factor = self.get_scale_factor()
            gbytes = GLib.Bytes(bytes)
            stream = Gio.MemoryInputStream.new_from_bytes(gbytes)
            if stream is not None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
                if self.__api is None:
                    text = "%sx%s" % (pixbuf.get_width(),
                                      pixbuf.get_height())
                else:
                    text = "%s: %sx%s" % (self.__api,
                                          pixbuf.get_width(),
                                          pixbuf.get_height())
                self.__label.set_text(text)
                pixbuf = App().art.load_behaviour(pixbuf,
                                                  None,
                                                  ArtSize.BIG * scale_factor,
                                                  ArtSize.BIG * scale_factor,
                                                  ArtBehaviour.CROP)
                stream.close()
            self.__bytes = bytes
            surface = Gdk.cairo_surface_create_from_pixbuf(
                                                   pixbuf,
                                                   scale_factor,
                                                   None)
            self.__image.set_from_surface(surface)
            return True
        except Exception as e:
            Logger.error("ArtworkSearch::__get_image: %s" % e)
        return False

    @property
    def bytes(self):
        """
            Get bytes associated to widget
            @return bytes
        """
        return self.__bytes


class ArtworkSearchWidget(Gtk.Bin, SignalsHelper):
    """
        Search for artwork
    """

    @signals
    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        self.__timeout_id = None
        self.__uri_artwork_id = None
        self.__uris = []
        self.__loaders = 0
        self._cancellable = Gio.Cancellable()
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtworkSearch.ui")
        builder.connect_signals(self)
        self.__infobar = builder.get_object("infobar")
        self.__infobar_label = builder.get_object("infobarlabel")
        widget = builder.get_object("widget")
        self.__stack = builder.get_object("stack")
        self.__entry = builder.get_object("entry")
        self.__api_entry = builder.get_object("api_entry")
        self.__back_button = builder.get_object("back_button")

        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._flowbox.connect("child-activated", self._on_activate)
        self._flowbox.set_max_children_per_line(100)
        self._flowbox.set_property("row-spacing", 10)
        self._flowbox.show()

        self.__label = builder.get_object("label")
        self.__label.set_text(_("Select artwork"))

        builder.get_object("viewport").add(self._flowbox)

        self.__spinner = builder.get_object("spinner")
        self.__stack.add_named(builder.get_object("scrolled"), "main")
        self.__stack.set_visible_child_name("main")
        self.add(widget)
        self.connect("unmap", self.__on_unmap)
        return {
            "init": [
                (App().art, "uri-artwork-found", "_on_uri_artwork_found")
            ]
        }

    def populate(self):
        """
            Populate view
        """
        try:
            grid = Gtk.Grid()
            grid.set_orientation(Gtk.Orientation.VERTICAL)
            grid.show()
            grid.set_row_spacing(5)
            image = Gtk.Image.new_from_icon_name("edit-clear-all-symbolic",
                                                 Gtk.IconSize.DIALOG)
            image.set_property("valign", Gtk.Align.CENTER)
            image.set_property("halign", Gtk.Align.CENTER)
            context = image.get_style_context()
            context.add_class("cover-frame")
            padding = context.get_padding(Gtk.StateFlags.NORMAL)
            border = context.get_border(Gtk.StateFlags.NORMAL)
            image.set_size_request(ArtSize.BIG + padding.left +
                                   padding.right + border.left + border.right,
                                   ArtSize.BIG + padding.top +
                                   padding.bottom + border.top + border.bottom)
            image.show()
            label = Gtk.Label.new(_("Remove"))
            label.show()
            grid.add(image)
            grid.add(label)
            self._flowbox.add(grid)
            self.__search_for_artwork()
        except Exception as e:
            Logger.error("ArtworkSearchWidget::populate(): %s", e)

    def stop(self):
        """
            Stop loading
        """
        self._cancellable.cancel()

#######################
# PROTECTED           #
#######################
    def _close_popover(self):
        """
            Search for a popover in parents and close it
        """
        widget = self.get_parent()
        while widget is not None:
            if isinstance(widget, Popover):
                widget.hide()
                break
            widget = widget.get_parent()

    def _get_current_search(self):
        """
            Return current searches
            @return str
        """
        search = ""
        if self.__entry.get_text() != "":
            search = self.__entry.get_text()
        return search

    def _search_from_downloader(self):
        """
            Load artwork from downloader
        """
        self.__loaders -= 1

    def _on_search_changed(self, entry):
        """
            Launch search based on current text
            @param entry as Gtk.Entry
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
        self.__timeout_id = GLib.timeout_add(1000,
                                             self.__on_search_timeout,
                                             entry.get_text())

    def _on_reset_confirm(self, button):
        """
            Reset cover
            @param button as Gtk.Button
        """
        self.__infobar.hide()
        self._close_popover()

    def _on_info_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()
            self._flowbox.unselect_all()

    def _on_activate(self, flowbox, child):
        """
            An artwork has been activated
            @param flowbox as Gtk.FlowBox
            @param child as ArtworkSearchChild
        """
        self.__infobar_label.set_text(_("Reset artwork?"))
        self.__infobar.show()
        # GTK 3.20 https://bugzilla.gnome.org/show_bug.cgi?id=710888
        self.__infobar.queue_resize()

    def _on_uri_artwork_found(self, art, uris):
        """
            Load content in view
            @param art as Art
            @param uris as (str, str)
        """
        if uris:
            (uri, api) = uris.pop(0)
            App().task_helper.load_uri_content(uri,
                                               self._cancellable,
                                               self.__on_load_uri_content,
                                               api,
                                               uris)
        else:
            self.__loaders -= 1
            if self.__loaders == 0:
                self.__spinner.stop()

#######################
# PRIVATE             #
#######################
    def __search_for_artwork(self):
        """
            Search artwork on the web
        """
        self.__uris = []
        self.__loaders = 3
        self._cancellable = Gio.Cancellable()
        search = self._get_current_search()
        self.__spinner.start()
        self._search_from_downloader()
        App().task_helper.run(App().art.search_artwork_from_google,
                              search,
                              self._cancellable)
        App().task_helper.run(App().art.search_artwork_from_startpage,
                              search,
                              self._cancellable)

    def __add_pixbuf(self, content, api):
        """
            Add content to view
            @param content as bytes
            @param api as str
        """
        child = ArtworkSearchChild(api)
        child.show()
        status = child.populate(content)
        if status:
            child.set_name("web")
            self._flowbox.add(child)
        else:
            child.destroy()

    def __on_unmap(self, widget):
        """
            Cancel loading
            @param widget as Gtk.Widget
        """
        self._cancellable.cancel()

    def __on_load_uri_content(self, uri, loaded, content, api, uris):
        """
            Add loaded pixbuf
            @param uri as str
            @param loaded as bool
            @param content as bytes
            @param uris as [str]
            @param api as str
            @param last as bool
        """
        try:
            if loaded:
                self.__add_pixbuf(content, api)
            if uris:
                (uri, api) = uris.pop(0)
                App().task_helper.load_uri_content(uri,
                                                   self._cancellable,
                                                   self.__on_load_uri_content,
                                                   api,
                                                   uris)
            else:
                self.__loaders -= 1
        except Exception as e:
            self.__loaders -= 1
            Logger.warning(
                "ArtworkSearchWidget::__on_load_uri_content(): %s", e)
        if self.__loaders == 0:
            self.__spinner.stop()

    def __on_search_timeout(self, string):
        """
            Populate widget
            @param string as str
        """
        self.__timeout_id = None
        self._cancellable.cancel()
        self._cancellable = Gio.Cancellable()
        for child in self._flowbox.get_children():
            if child.get_name() == "web":
                child.destroy()
        GLib.timeout_add(500, self.__search_for_artwork)
