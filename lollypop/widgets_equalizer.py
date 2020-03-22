# Copyright (c) 2014-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (C) 2010 Jonathan Matthew (replay gain code)
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

from gettext import gettext as _

from lollypop.define import App
from lollypop.widgets_combobox import ComboBox


PRESETS = {
           _("Default"): (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
           _("Custom"): (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
           "Separator": (),
           _("Classical"): (0, 0, 0, 0, 0, 0, -4, -4, -4, -6),
           _("Club"): (0, 0, 2, 3, 3, 3, 2, 0, 0, 0),
           _("Dance"): (6, 4, 1, 0, 0, -3, -4, -4, 0, 0),
           _("Dubstep"): (0, 4, 10, 6, 3, 0, 4, 7, 11, 7),
           _("Full Bass"): (8, 8, 8, 4, 2, -5, -6, -6, -6, -6),
           _("Full Treble"): (-6, -6, -6, -3, 1, 6, 9, 9, 9, 10),
           _("Full Bass + Treble"): (4, 3, 0, -4, -3, 1, 5, 6, 7, 7),
           _("Hip Hop"): (10, 12, 12, -2, -3, 1, 12, 0, 6, 8),
           _("Kuduro"): (7, -12, 1, 7, -4, 10, 12, -5, 2, -12),
           _("Laptop/Headphones"): (3, 6, 3, -2, 0, -3, -4, -4, 0, 0),
           _("Large Hall"): (6, 6, 3, 3, 0, -3, -3, -3, 0, 0),
           _("Live"): (-3, 0, 2, 3, 3, 3, 2, 1, 1, 1),
           _("Party"): (4, 4, 0, 0, 0, 0, 0, 0, 4, 4),
           _("Pop"): (-1, 3, 4, 4, 3, 0, -1, -1, -1, -1),
           _("Psychedelic"): (12, 12, 0, 4, 0, 8, 9, 0, 3, -12),
           _("Reggae"): (0, 0, 0, -3, 0, -4, -4, 0, 0, 0),
           _("Rock"): (4, 3, -3, -4, -2, 2, 5, 6, 6, 6),
           _("Soft"): (3, 1, 0, -1, 0, 2, 5, 6, 6, 7),
           _("Ska"): (-1, -3, -3, 0, 2, 3, 5, 6, 6, 6),
           _("Soft Rock"): (2, 2, 1, 0, -3, -3, -2, 0, 1, 5),
           _("Techno"): (4, 3, 0, -3, -3, 0, 4, 6, 6, 5),
}


class EqualizerWidget(Gtk.Bin):
    """
        An equalizer manager widget
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        self.set_property("valign", Gtk.Align.START)
        self.set_property("halign", Gtk.Align.CENTER)
        self.__timeout_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/EqualizerWidget.ui")
        self.__combobox = ComboBox()
        self.__combobox.show()
        self.__combobox.connect("changed", self.__on_combobox_changed)
        builder.get_object("header_box").pack_end(self.__combobox,
                                                  False, False, 0)
        equalizer = App().settings.get_value("equalizer")
        enabled_equalizer = App().settings.get_value("equalizer-enabled")
        if enabled_equalizer:
            builder.get_object("equalizer_checkbox").set_active(True)
        else:
            self.__combobox.set_sensitive(False)
        for i in range(0, 10):
            scale = builder.get_object("scale%s" % i)
            scale.set_value(equalizer[i])
            setattr(self, "__scale%s" % i, scale)
            scale.connect("value-changed", self.__on_scale_value_changed, i)
            scale.set_sensitive(enabled_equalizer)
        self.add(builder.get_object("widget"))
        preset = ()
        for i in App().settings.get_value("equalizer"):
            preset += (i,)
        for key in PRESETS.keys():
            self.__combobox.append(key)
        self.__set_combobox_value()
        builder.connect_signals(self)

    def do_get_preferred_width(self):
        return (250, 600)

#######################
# PROTECTED           #
#######################
    def _on_format_value(self, scale, value):
        """
            Format scale value
            @param scale as Gtk.Scale
            @param value as float
            @return str
        """
        return "%s dB" % value

    def _on_equalizer_checkbox_toggled(self, button):
        """
            Enable/disable equalizer
            @param button as Gtk.ToggleButton
        """
        active = button.get_active()
        App().settings.set_value("equalizer-enabled",
                                 GLib.Variant("b", active))
        for plugin in App().player.plugins:
            plugin.build_audiofilter()
        App().player.reload_track()
        self.__combobox.set_sensitive(active)
        for i in range(0, 10):
            attr = getattr(self, "__scale%s" % i)
            attr.set_sensitive(active)

#######################
# PRIVATE             #
#######################
    def __set_combobox_value(self):
        """
            Set combobox value based on current equalizer
        """
        combo_set = False
        preset = ()
        for i in App().settings.get_value("equalizer"):
            preset += (i,)
        for key in PRESETS.keys():
            if preset == PRESETS[key]:
                self.__combobox.set_active_id(key)
                combo_set = True
                break
        if not combo_set:
            App().settings.set_value("equalizer-custom",
                                     GLib.Variant("ad", preset))
            self.__combobox.set_active_id(_("Custom"))

    def __save_equalizer(self):
        """
            Save equalizer to gsettings
        """
        self.__timeout_id = None
        preset = []
        for i in range(0, 10):
            attr = getattr(self, "__scale%s" % i)
            preset.append(attr.get_value())
        App().settings.set_value("equalizer", GLib.Variant("ad", preset))
        self.__set_combobox_value()

    def __on_scale_value_changed(self, scale, band):
        """
            Update equalizer
            @param scale as Gtk.Scale
            @param band as int
        """
        for plugin in App().player.plugins:
            plugin.set_equalizer(band, scale.get_value())
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
        self.__timeout_id = GLib.timeout_add(250, self.__save_equalizer)

    def __on_combobox_changed(self, combobox):
        """
            Update check combobox
            @param combobox as Gtk.ComboBoxText
        """
        key = combobox.get_active_id()
        if key == _("Custom"):
            preset = App().settings.get_value("equalizer-custom")
            App().settings.set_value("equalizer", preset)
            for plugin in App().player.plugins:
                plugin.update_equalizer()
            PRESETS[key] = preset
        keys = PRESETS.keys()
        if key in keys:
            values = PRESETS[key]
            i = 0
            for value in values:
                attr = getattr(self, "__scale%s" % i)
                attr.set_value(value)
                i += 1
