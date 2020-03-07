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

from gi.repository import Gtk

from gettext import gettext as _

from lollypop.view import View
from lollypop.define import App, Type, StorageType


class SettingsViewRow(Gtk.ListBoxRow):
    """
        A row for settings view
    """

    def __init__(self, row_type):
        """
            Init row
            @param row_type as int
        """
        Gtk.ListBoxRow.__init__(self)
        self.set_margin_top(10)
        self.set_margin_bottom(10)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.__row_type = row_type
        if row_type == Type.SETTINGS_APPEARANCE:
            main_label = Gtk.Label.new(_("Appearance"))
            sub_label = Gtk.Label.new(_("Configure Lollypop appearance"))
        elif row_type == Type.SETTINGS_BEHAVIOUR:
            main_label = Gtk.Label.new(_("Behaviour"))
            sub_label = Gtk.Label.new(_("Configure Lollypop behaviour"))
        elif row_type == Type.SETTINGS_COLLECTIONS:
            main_label = Gtk.Label.new(_("Music"))
            sub_label = Gtk.Label.new(_("Select music folders"))
        elif row_type == Type.SETTINGS_WEB:
            main_label = Gtk.Label.new(_("Web"))
            sub_label = Gtk.Label.new(_("Configure Web services"))
        elif row_type == Type.SETTINGS_DEVICES:
            main_label = Gtk.Label.new(_("Devices"))
            sub_label = Gtk.Label.new(_("Manage devices"))
        main_label.set_property("halign", Gtk.Align.START)
        main_label.get_style_context().add_class("bold")
        sub_label.set_property("halign", Gtk.Align.START)
        sub_label.get_style_context().add_class("dim-label")
        main_label.show()
        sub_label.show()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        grid.set_margin_start(5)
        grid.add(main_label)
        grid.add(sub_label)
        grid.show()
        self.add(grid)

    @property
    def type(self):
        """
            Get row type
            @return row_type as int
        """
        return self.__row_type


class SettingsView(View):
    """
        Show settings selector
    """

    def __init__(self, view_type):
        """
            Init view
            @param view_type as ViewType
        """
        View.__init__(self, StorageType.ALL, view_type)
        self.__listbox = Gtk.ListBox()
        self.__listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__listbox.get_style_context().add_class("sidebar")
        self.__listbox.connect("row-activated", self.__on_row_activated)
        self.__listbox.show()
        for row_type in [Type.SETTINGS_APPEARANCE,
                         Type.SETTINGS_BEHAVIOUR,
                         Type.SETTINGS_COLLECTIONS,
                         Type.SETTINGS_WEB,
                         Type.SETTINGS_DEVICES]:
            row = SettingsViewRow(row_type)
            row.show()
            self.__listbox.add(row)
        self.add_widget(self.__listbox)

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return {}
        """
        return {"view_type": self.view_type}

    @property
    def type(self):
        """
            Get view type
            @return type as int
        """
        return Type.SETTINGS

##############
# PROTECTED  #
##############
    def _on_map(self, widget):
        """
            Disable settings action
            @param widget as Gtk.Widget
        """
        View._on_map(self, widget)
        App().lookup_action("settings").set_enabled(False)

    def _on_unmap(self, widget):
        """
            Enable settings action
            @param widget as Gtk.Widget
        """
        View._on_unmap(self, widget)
        App().lookup_action("settings").set_enabled(True)

############
# PRIVATE  #
############
    def __on_row_activated(self, listbox, row):
        """
            Show wanted view
            @param listbox as Gtk.ListBox
            @param row as SettingsViewRow
        """
        App().window.container.show_view([row.type])


class SettingsChildView(View):
    """
        Show settings widget
    """

    def __init__(self, view_id, view_type):
        """
            Init view
            @param view_id as int
            @param view_type as ViewType
        """
        View.__init__(self, StorageType.ALL, view_type)
        self.__view_id = view_id
        if view_id == Type.SETTINGS_APPEARANCE:
            from lollypop.widgets_settings_appearance\
                import AppearanceSettingsWidget
            widget = AppearanceSettingsWidget()
        elif view_id == Type.SETTINGS_BEHAVIOUR:
            from lollypop.widgets_settings_behaviour\
                import BehaviourSettingsWidget
            widget = BehaviourSettingsWidget()
        elif view_id == Type.SETTINGS_COLLECTIONS:
            from lollypop.widgets_settings_collections\
                import CollectionsSettingsWidget
            widget = CollectionsSettingsWidget()
        elif view_id == Type.SETTINGS_WEB:
            from lollypop.widgets_settings_web\
                import WebSettingsWidget
            widget = WebSettingsWidget()
        elif view_id == Type.SETTINGS_DEVICES:
            from lollypop.widgets_settings_devices\
                import DevicesSettingsWidget
            widget = DevicesSettingsWidget()
        child = widget.get_child()
        if isinstance(child, Gtk.Box):
            child.set_spacing(20)
        widget.show()
        self.add_widget(widget)

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return {}
        """
        return {"view_id": self.__view_id,
                "view_type": self.view_type},

    @property
    def type(self):
        """
            Get type
            @return type as int
        """
        return self.__view_id

##############
# PROTECTED  #
##############
    def _on_map(self, widget):
        """
            Disable settings action
            @param widget as Gtk.Widget
        """
        App().lookup_action("settings").set_enabled(False)
        App().enable_special_shortcuts(False)

    def _on_unmap(self, widget):
        """
            Enable settings action
            @param widget as Gtk.Widget
        """
        App().lookup_action("settings").set_enabled(True)
        App().enable_special_shortcuts(True)
