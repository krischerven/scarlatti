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

from gi.repository import Gtk, Pango, GObject

from lollypop.define import App, ArtSize, ArtBehaviour, ViewType, MARGIN_SMALL
from lollypop.utils import on_query_tooltip, set_cursor_type
from lollypop.objects_radio import Radio


class RadioWidget(Gtk.FlowBoxChild):
    """
        Widget with radio cover and title
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, radio_id, view_type, font_height):
        """
            Init radio widget
            @param radio_id as int
            @param view_type as ViewType
            @param font_height as int
        """
        Gtk.FlowBoxChild.__init__(self)
        self.__artwork = None
        self.__font_height = font_height
        self._track = Radio(radio_id)
        self.__view_type = view_type
        self.set_view_type(view_type)

    def populate(self):
        """
            Init widget content
        """
        if self.__artwork is None:
            grid = Gtk.Grid()
            grid.set_row_spacing(MARGIN_SMALL)
            grid.set_orientation(Gtk.Orientation.VERTICAL)
            grid.show()
            self.__artwork = Gtk.Image.new()
            self.__artwork.connect("realize", set_cursor_type)
            self.__artwork.show()
            self.__label = Gtk.Label.new()
            self.__label.set_justify(Gtk.Justification.CENTER)
            self.__label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__label.set_text(self._track.name)
            self.__label.get_style_context().add_class("big-padding")
            self.__label.set_property("has-tooltip", True)
            self.__label.connect("query-tooltip", on_query_tooltip)
            self.__label.show()
            self.__spinner = Gtk.Spinner.new()
            self.__spinner.get_style_context().add_class("big-padding")
            self.__spinner.show()
            self.__stack = Gtk.Stack.new()
            self.__stack.show()
            self.__stack.add(self.__label)
            self.__stack.add(self.__spinner)
            grid.add(self.__artwork)
            grid.add(self.__stack)
            self.add(grid)
            self.set_artwork()
            self.set_selection()
            self.show()
        else:
            self.set_artwork()

    def disable_artwork(self):
        """
            Disable widget artwork
        """
        if self.__artwork is not None:
            self.__artwork.set_size_request(self.__art_size, self.__art_size)
            self.__artwork.set_from_surface(None)

    def set_artwork(self):
        """
            Set artwork
        """
        if self.__artwork is None:
            return
        if self.__art_size < ArtSize.BIG:
            frame = "small-cover-frame"
        else:
            frame = "cover-frame"
        App().art_helper.set_frame(self.__artwork,
                                   frame,
                                   self.__art_size,
                                   self.__art_size)
        App().art_helper.set_radio_artwork(self._track.name,
                                           self.__art_size,
                                           self.__art_size,
                                           self.__artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE |
                                           ArtBehaviour.CROP,
                                           self.__on_radio_artwork)

    def set_view_type(self, view_type):
        """
            Update artwork size
            @param view_type as ViewType
        """
        self.__view_type = view_type
        if self.__view_type & ViewType.SMALL:
            self.__art_size = ArtSize.MEDIUM
        elif self.__view_type & ViewType.ADAPTIVE:
            self.__art_size = ArtSize.BANNER
        else:
            self.__art_size = ArtSize.BIG
        self.set_size_request(self.__art_size,
                              self.__art_size + self.__font_height)

    def set_loading(self, loading):
        """
            Show spinner
            @param loading as bool
        """
        if loading:
            self.__spinner.start()
            self.__stack.set_visible_child(self.__spinner)
        else:
            self.__spinner.stop()
            self.__stack.set_visible_child(self.__label)

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self.__artwork is None:
            return (0, 0)
        width = Gtk.FlowBoxChild.do_get_preferred_width(self)[0]
        return (width, width)

    def rename(self, name):
        """
            Set radio name
            @param name as str
        """
        self.__label.set_label(name)

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        if self.__artwork is None:
            return
        selected = isinstance(App().player.current_track.id, Radio) and\
            self._track.id == App().player.current_track.id
        if selected:
            self.__artwork.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self.__artwork.set_state_flags(Gtk.StateFlags.NORMAL, True)

    @property
    def spinner(self):
        """
            Get radio spinner
        """
        return self.__spinner

    @property
    def is_populated(self):
        """
            True if album populated
            @return bool
        """
        return True

    @property
    def artwork(self):
        """
            Get album artwork
            @return Gtk.Image
        """
        return self.__artwork

    @property
    def name(self):
        """
            Get name
            @return str
        """
        return self.__label.get_text()

    @property
    def data(self):
        """
            Get track
            @return int
        """
        return self._track

#######################
# PROTECTED           #
#######################
    def _on_loading_changed(self, player, status, track_id):
        """
            Show a spinner while loading
            @param player as Player
            @param status as bool
            @param track_id as int
        """
        if track_id != self._track.id:
            return

#######################
# PRIVATE             #
#######################
    def __on_radio_artwork(self, surface):
        """
            Set radio artwork
            @param surface as str
        """
        if surface is None:
            self.__artwork.set_from_icon_name(
                                             "audio-input-microphone-symbolic",
                                             Gtk.IconSize.DIALOG)
        else:
            self.__artwork.set_from_surface(surface)
        self.emit("populated")
