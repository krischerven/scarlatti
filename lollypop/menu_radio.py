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

from gi.repository import Gtk, Gio, GObject

from gettext import gettext as _

from lollypop.widgets_rating import RatingWidget
from lollypop.define import App, ArtSize, ArtBehaviour, MARGIN, MARGIN_SMALL
from lollypop.define import ViewType
from lollypop.widgets_artwork_radio import RadioArtworkSearchWidget
from lollypop.art import Art
from lollypop.utils import emit_signal
from lollypop.objects_radio import Radio


class RadioMenu(Gtk.Grid):
    """
        Popover with radio logos from the web
    """

    __gsignals__ = {
        "hidden": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self, radio, view_type):
        """
            Init Popover
            @param radio as Radio
            @param view_type as ViewType
            @param header as bool
        """
        Gtk.Grid.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.__view_type = view_type
        self.__uri_artwork_id = None
        self.__radio = radio if radio is not None else Radio(None)

        self.set_row_spacing(MARGIN)
        self.set_margin_start(MARGIN_SMALL)
        self.set_margin_end(MARGIN_SMALL)
        self.set_margin_top(MARGIN)
        self.set_margin_bottom(MARGIN)

        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(1000)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadioMenu.ui")
        builder.connect_signals(self)

        self.__name_entry = builder.get_object("name")
        self.__uri_entry = builder.get_object("uri")
        self.__artwork_button = builder.get_object("artwork_button")
        self.__save_button = builder.get_object("save_button")
        self.__stack.add_named(builder.get_object("widget"), "widget")
        self.__stack.set_visible_child_name("widget")

        if view_type & ViewType.ADAPTIVE:
            button = Gtk.ModelButton.new()
            button.set_alignment(0, 0.5)
            button.connect("clicked",
                           lambda x: emit_signal(self, "hidden", True))
            button.show()
            label = Gtk.Label.new()
            label.show()
            if self.__radio.name:
                self.__artwork = Gtk.Image.new()
                name = "<span alpha='40000'>%s</span>" % radio.name
                App().art_helper.set_radio_artwork(
                                           self.__radio.name,
                                           ArtSize.SMALL,
                                           ArtSize.SMALL,
                                           self.__artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE |
                                           ArtBehaviour.CROP,
                                           self.__on_radio_artwork)
            else:
                self.__artwork = Gtk.Image.new_from_icon_name(
                    "org.gnome.Lollypop-gradio-symbolic",
                    Gtk.IconSize.INVALID)
                self.__artwork.set_pixel_size(ArtSize.SMALL)
                name = "<span alpha='40000'>%s</span>" % _("New radio")
            self.__artwork.show()
            label.set_markup(name)
            grid = Gtk.Grid()
            grid.set_column_spacing(MARGIN)
            grid.add(self.__artwork)
            grid.add(label)
            button.set_image(grid)
            button.get_style_context().add_class("padding")
            self.add(button)
        self.add(self.__stack)
        if radio is not None:
            if view_type & ViewType.ADAPTIVE:
                rating = RatingWidget(radio, Gtk.IconSize.DND)
            else:
                rating = RatingWidget(radio)
            rating.show()
            builder.get_object("widget").attach(rating, 0, 2, 2, 1)
            builder.get_object("delete_button").show()
            self.__name_entry.set_text(radio.name)
            if radio.uri:
                self.__uri_entry.set_text(radio.uri)

#######################
# PROTECTED           #
#######################
    def _on_save_button_clicked(self, widget):
        """
            Save radio
            @param widget as Gtk.Widget
        """
        self.__save_radio()
        emit_signal(self, "hidden", True)

    def _on_delete_button_clicked(self, widget):
        """
            Delete a radio
            @param widget as Gtk.Widget
        """
        if self.__radio.id is not None:
            store = Art._RADIOS_PATH
            name = self.__radio.name
            App().radios.remove(self.__radio.id)
            App().art.uncache_radio_artwork(name)
            f = Gio.File.new_for_path(store + "/%s.png" % name)
            if f.query_exists():
                f.delete()
        emit_signal(self, "hidden", True)

    def _on_entry_changed(self, entry):
        """
            Update modify/add button
            @param entry as Gtk.Entry
        """
        uri = self.__uri_entry.get_text()
        name = self.__name_entry.get_text()
        if name != "" and uri.find("://") != -1:
            self.__artwork_button.set_sensitive(True)
            self.__save_button.set_sensitive(True)
        else:
            self.__artwork_button.set_sensitive(False)
            self.__save_button.set_sensitive(False)

    def _on_artwork_button_clicked(self, widget):
        """
            Update radio image
            @param widget as Gtk.Widget
        """
        self.__stack.get_visible_child().hide()
        self.__save_radio()
        name = App().radios.get_name(self.__radio.id)
        artwork_widget = RadioArtworkSearchWidget(name, self.__view_type)
        artwork_widget.populate()
        artwork_widget.show()
        artwork_widget.connect("hidden",
                               lambda x, y: emit_signal(self, "hidden", True))
        self.__stack.add_named(artwork_widget, "artwork")
        self.__stack.set_visible_child_name("artwork")

#######################
# PRIVATE             #
#######################
    def __save_radio(self):
        """
            Save radio based on current widget content
        """
        new_name = self.__name_entry.get_text()
        new_uri = self.__uri_entry.get_text()
        if new_name != "" and new_uri != "":
            if self.__radio.id is None:
                radio_id = App().radios.add(new_name,
                                            new_uri.lstrip().rstrip())
                self.__radio = Radio(radio_id)
            else:
                name = App().radios.get_name(self.__radio.id)
                App().radios.rename(self.__radio.id, new_name)
                App().radios.set_uri(self.__radio.id, new_uri)
                App().art.rename_radio(name, new_name)
                self.__radio.set_uri(new_uri)
                self.__radio.set_name(new_name)

    def __on_radio_artwork(self, surface):
        """
            Set radio artwork
            @param surface as str
        """
        if surface is None:
            self.__artwork.set_from_icon_name(
                                             "audio-input-microphone-symbolic",
                                             Gtk.IconSize.BUTTON)
        else:
            self.__artwork.set_from_surface(surface)
            del surface
