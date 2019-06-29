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

from lollypop.define import App, ArtSize, Type, ArtBehaviour
from lollypop.utils import on_query_tooltip
from lollypop.helper_overlay_radio import OverlayRadioHelper


class RadioWidget(Gtk.FlowBoxChild, OverlayRadioHelper):
    """
        Widget with radio cover and title
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    ctx = App().window.get_pango_context()
    layout = Pango.Layout.new(ctx)
    layout.set_text("a", 1)
    # * 2 => two labels
    LABEL_HEIGHT = int(layout.get_pixel_size()[1])

    def __init__(self, radio_id, radios):
        """
            Init radio widget
            @param radio_id as int
            @param label_height as int
            @param radios as Radios
        """
        Gtk.FlowBoxChild.__init__(self)
        OverlayRadioHelper.__init__(self)
        self._widget = None
        self._artwork = None
        self._watch_loading = True
        self.__art_size = 120\
            if App().window.is_adaptive\
            else ArtSize.BIG
        self.set_size_request(self.__art_size,
                              self.__art_size + self.LABEL_HEIGHT)
        self._radio_id = radio_id
        self._radios = radios

    def populate(self):
        """
            Init widget content
        """
        name = self._radios.get_name(self._radio_id)
        self._widget = Gtk.EventBox()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._artwork = Gtk.Image.new()
        App().art_helper.set_frame(self._artwork,
                                   "cover-frame",
                                   self.__art_size,
                                   self.__art_size)
        self.__label = Gtk.Label.new()
        self.__label.set_justify(Gtk.Justification.CENTER)
        self.__label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__label.set_text(name)
        self.__label.set_property("has-tooltip", True)
        self.__label.connect("query-tooltip", on_query_tooltip)
        self._widget.add(grid)
        self._overlay = Gtk.Overlay.new()
        self._overlay.add(self._artwork)
        grid.add(self._overlay)
        grid.add(self.__label)
        self.add(self._widget)
        self.set_artwork()
        self.set_selection()
        self.show_all()
        self._lock_overlay = False
        self.set_property("halign", Gtk.Align.CENTER)
        self.set_property("valign", Gtk.Align.CENTER)
        self._widget.connect("enter-notify-event", self._on_enter_notify)
        self._widget.connect("leave-notify-event", self._on_leave_notify)

    def set_artwork(self):
        """
            Set album artwork
        """
        if self._widget is None:
            return
        name = self._radios.get_name(self._radio_id)
        App().art_helper.set_radio_artwork(name,
                                           self.__art_size,
                                           self.__art_size,
                                           self._artwork.get_scale_factor(),
                                           ArtBehaviour.CACHE,
                                           self.__on_radio_artwork)

    def set_sensitive(self, b):
        """
            Ignore set sensitive
        """
        pass

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self._widget is None:
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
        if self._artwork is None:
            return
        name = self._radios.get_name(self._radio_id)
        selected = App().player.current_track.id == Type.RADIOS and\
            name == App().player.current_track.radio_name
        if selected:
            self._artwork.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self._artwork.set_state_flags(Gtk.StateFlags.NORMAL, True)

    @property
    def is_populated(self):
        """
            True if album populated
            @return bool
        """
        return True

    @property
    def id(self):
        """
            @return int
        """
        return self._radio_id

    @property
    def filter(self):
        """
            @return filter as str
        """
        return self.name.lower()

    @property
    def name(self):
        """
            @return name as str
        """
        return self._radios.get_name(self._radio_id)

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_radio_artwork(self, surface):
        """
            Set radio artwork
            @param surface as str
        """
        if surface is None:
            self._artwork.set_from_icon_name("audio-input-microphone-symbolic",
                                             Gtk.IconSize.DIALOG)
        else:
            self._artwork.set_from_surface(surface)
        self.show_all()
        self.emit("populated")
