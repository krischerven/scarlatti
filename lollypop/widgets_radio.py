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

from lollypop.define import App, ArtSize, ArtBehaviour, ViewType
from lollypop.utils import on_query_tooltip
from lollypop.objects_radio import Radio
from lollypop.helper_overlay_radio import OverlayRadioHelper


class RadioWidget(Gtk.FlowBoxChild, OverlayRadioHelper):
    """
        Widget with radio cover and title
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "overlayed": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, radio_id, view_type, font_height):
        """
            Init radio widget
            @param radio_id as int
            @param radios as Radios
            @param view_type as ViewType
            @param font_height as int
        """
        Gtk.FlowBoxChild.__init__(self)
        OverlayRadioHelper.__init__(self)
        self.__widget = None
        self._artwork = None
        self.__font_height = font_height
        self._track = Radio(radio_id)
        self.__view_type = view_type
        self._watch_loading = True
        self.set_view_type(view_type)
        self.connect("activate", self.__on_activate)

    def populate(self):
        """
            Init widget content
        """
        if self._artwork is None:
            self.__widget = Gtk.EventBox()
            grid = Gtk.Grid()
            grid.set_orientation(Gtk.Orientation.VERTICAL)
            self._artwork = Gtk.Image.new()
            self.__label = Gtk.Label.new()
            self.__label.set_justify(Gtk.Justification.CENTER)
            self.__label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__label.set_text(self._track.name)
            self.__label.set_property("has-tooltip", True)
            self.__label.connect("query-tooltip", on_query_tooltip)
            self.__widget.add(grid)
            self._overlay = Gtk.Overlay.new()
            self._overlay.add(self._artwork)
            grid.add(self._overlay)
            grid.add(self.__label)
            self.add(self.__widget)
            self.set_artwork()
            self.set_selection()
            self.show_all()
            self._lock_overlay = False
            self.set_property("halign", Gtk.Align.CENTER)
            self.set_property("valign", Gtk.Align.CENTER)
            self.__widget.connect("enter-notify-event", self._on_enter_notify)
            self.__widget.connect("leave-notify-event", self._on_leave_notify)
        else:
            self.set_artwork()

    def disable_artwork(self):
        """
            Disable widget artwork
        """
        if self._artwork is not None:
            self._artwork.set_size_request(self.__art_size, self.__art_size)
            self._artwork.set_from_surface(None)

    def set_artwork(self):
        """
            Set artwork
        """
        if self.__widget is None:
            return
        if self.__art_size < ArtSize.BIG:
            frame = "small-cover-frame"
        else:
            frame = "cover-frame"
        App().art_helper.set_frame(self._artwork,
                                   frame,
                                   self.__art_size,
                                   self.__art_size)
        App().art_helper.set_radio_artwork(self._track.name,
                                           self.__art_size,
                                           self.__art_size,
                                           self._artwork.get_scale_factor(),
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
            self.__art_size = ArtSize.LARGE
        elif self.__view_type & ViewType.MEDIUM:
            self.__art_size = ArtSize.BANNER
        else:
            self.__art_size = ArtSize.BIG
        self.set_size_request(self.__art_size,
                              self.__art_size + self.__font_height)

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        if self.__widget is None:
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
        selected = isinstance(App().player.current_track.id, Radio) and\
            self._track.id == App().player.current_track.id
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
    def track(self):
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
        OverlayRadioHelper._on_loading_changed(self, player, status, track_id)

#######################
# PRIVATE             #
#######################
    def __on_activate(self, child):
        """
            Play radio
            @param child as Gtk.FlowBoxChild
        """
        App().player.load(self.__track)

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
