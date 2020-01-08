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

from gi.repository import Gtk, Gdk

from gettext import gettext as _

from lollypop.define import App, Type
from lollypop.widgets_settings_appearance import AppearanceSettingsWidget
from lollypop.widgets_settings_behaviour import BehaviourSettingsWidget
from lollypop.widgets_settings_collections import CollectionsSettingsWidget
from lollypop.widgets_settings_web import WebSettingsWidget
from lollypop.widgets_settings_devices import DevicesSettingsWidget


class SettingsDialog:
    """
        Dialog showing lollypop options
    """

    def __init__(self, dialog_type):
        """
            Init dialog
            @param dialog_type as int
        """
        self.__choosers = []
        self.__mix_tid = None
        self.__popover = None

        appearance_widget = AppearanceSettingsWidget()
        appearance_widget.show()
        appearance_label = Gtk.Label.new(_("Appearance"))
        appearance_label.set_tooltip_text(_("Configure Lollypop appearance"))
        appearance_label.show()
        behaviour_widget = BehaviourSettingsWidget()
        behaviour_widget.show()
        behaviour_label = Gtk.Label.new(_("Behaviour"))
        behaviour_label.set_tooltip_text(_("Configure Lollypop behaviour"))
        behaviour_label.show()
        collections_widget = CollectionsSettingsWidget()
        collections_widget.show()
        collections_label = Gtk.Label.new(_("Music"))
        collections_label.set_tooltip_text(_("Select music folders"))
        collections_label.show()
        web_widget = WebSettingsWidget()
        web_widget.show()
        web_label = Gtk.Label.new(_("Web"))
        web_label.set_tooltip_text(_("Configure Web services"))
        web_label.show()
        device_widget = DevicesSettingsWidget()
        device_widget.show()
        device_label = Gtk.Label.new(_("Devices"))
        device_label.set_tooltip_text(_("Manage devices"))
        device_label.show()

        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsDialog.ui")
        notebook = builder.get_object("notebook")
        notebook.append_page(appearance_widget, appearance_label)
        notebook.append_page(behaviour_widget, behaviour_label)
        notebook.append_page(collections_widget, collections_label)
        notebook.append_page(web_widget, web_label)
        devices = list(filter(("").__ne__,
                              App().settings.get_value("devices")))
        if devices:
            notebook.append_page(device_widget, device_label)

        if dialog_type == Type.SETTINGS_BEHAVIOUR:
            notebook.set_current_page(1)
        elif dialog_type == Type.SETTINGS_COLLECTIONS:
            notebook.set_current_page(2)
        elif dialog_type == Type.SETTINGS_WEB:
            notebook.set_current_page(3)

        self.__settings_dialog = builder.get_object("settings_dialog")
        self.__settings_dialog.set_transient_for(App().window)

        if App().settings.get_value("disable-csd"):
            self.__settings_dialog.set_title(_("Preferences"))
        else:
            headerbar = builder.get_object("header_bar")
            headerbar.set_title(_("Preferences"))
            self.__settings_dialog.set_titlebar(headerbar)
        builder.connect_signals(self)

    def show(self):
        """
            Show dialog
        """
        self.__settings_dialog.show()

#######################
# PROTECTED           #
#######################
    def _on_key_press_event(self, widget, event):
        """
            Destroy window if Esc
            @param widget as Gtk.Widget
            @param event as Gdk.event
        """
        if event.keyval == Gdk.KEY_Escape:
            self.__settings_dialog.destroy()

#######################
# PRIVATE             #
#######################
