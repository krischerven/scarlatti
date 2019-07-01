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

from gi.repository import Gtk, Gio

from lollypop.objects import Track
from lollypop.widgets_rating import RatingWidget
from lollypop.define import App
from lollypop.widgets_utils import Popover
from lollypop.widgets_artwork_radio import RadioArtworkSearchWidget
from lollypop.art import Art


# Show a popover with radio logos from the web
class RadioPopover(Popover):
    """
        Popover with radio logos from the web
    """

    def __init__(self, radio_id, radios):
        """
            Init Popover
            @param radio_id as int
            @param radios as Radios
        """
        Popover.__init__(self)
        self.__uri_artwork_id = None
        self.__radio_id = radio_id
        self.__radios = radios

        self.__stack = Gtk.Stack()
        self.__stack.set_transition_duration(1000)
        self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.__stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/RadioPopover.ui")
        builder.connect_signals(self)

        self.__name_entry = builder.get_object("name")
        self.__uri_entry = builder.get_object("uri")
        self.__image_button = builder.get_object("image_button")
        self.__save_button = builder.get_object("save_button")
        self.__stack.add_named(builder.get_object("widget"), "widget")
        self.__stack.set_visible_child_name("widget")
        self.add(self.__stack)

        track = Track()
        if radio_id is not None:
            name = self.__radios.get_name(radio_id)
            track.set_radio_id(radio_id)
            rating = RatingWidget(track)
            rating.show()
            builder.get_object("widget").attach(rating, 0, 2, 2, 1)
            builder.get_object("delete_button").show()
            self.__name_entry.set_text(name)
            uri = self.__radios.get_uri(radio_id)
            if uri:
                self.__uri_entry.set_text(uri)

#######################
# PROTECTED           #
#######################
    def _on_save_button_clicked(self, widget):
        """
            Save radio
            @param widget as Gtk.Widget
        """
        self.popdown()
        self.__save_radio()

    def _on_delete_button_clicked(self, widget):
        """
            Delete a radio
            @param widget as Gtk.Widget
        """
        self.popdown()
        if self.__radio_id is not None:
            store = Art._RADIOS_PATH
            name = self.__radios.get_name(self.__radio_id)
            self.__radios.remove(self.__radio_id)
            App().art.uncache_radio_artwork(name)
            f = Gio.File.new_for_path(store + "/%s.png" % name)
            if f.query_exists():
                f.delete()

    def _on_entry_changed(self, entry):
        """
            Update modify/add button
            @param entry as Gtk.Entry
        """
        uri = self.__uri_entry.get_text()
        name = self.__name_entry.get_text()
        if name != "" and uri.find("://") != -1:
            self.__image_button.set_sensitive(True)
            self.__save_button.set_sensitive(True)
        else:
            self.__image_button.set_sensitive(False)
            self.__save_button.set_sensitive(False)

    def _on_image_button_clicked(self, widget):
        """
            Update radio image
            @param widget as Gtk.Widget
        """
        self.__stack.get_visible_child().hide()
        self.__save_radio()
        name = self.__radios.get_name(self.__radio_id)
        artwork_widget = RadioArtworkSearchWidget(name)
        artwork_widget.populate()
        artwork_widget.show()
        self.__stack.add_named(artwork_widget, "artwork")
        self.__stack.set_visible_child_name("artwork")
        self.set_size_request(700, 400)

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
            if self.__radio_id is None:
                self.__radio_id = self.__radios.add(
                    new_name, new_uri.lstrip().rstrip())
            else:
                name = self.__radios.get_name(self.__radio_id)
                self.__radios.rename(self.__radio_id, new_name)
                self.__radios.set_uri(self.__radio_id, new_uri)
                App().art.rename_radio(name, new_name)
