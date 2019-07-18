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

from gi.repository import Gtk, GLib

from lollypop.define import App, Type
from lollypop.view import View
from lollypop.adaptive import AdaptiveStack
from lollypop.container_notification import NotificationContainer
from lollypop.container_scanner import ScannerContainer
from lollypop.container_playlists import PlaylistsContainer
from lollypop.container_lists import ListsContainer
from lollypop.container_views import ViewsContainer
from lollypop.container_filter import FilterContainer
from lollypop.progressbar import ProgressBar


class ContainerStack(AdaptiveStack):
    """
        Glue for filtering between stack and current view
    """

    def __init__(self):
        """
            Init stack
        """
        AdaptiveStack.__init__(self)

    def search_for_child(self, text):
        view = self.get_visible_child()
        if view is not None and hasattr(view, "search_for_child"):
            view.search_for_child(text)

    def activate_child(self):
        view = self.get_visible_child()
        if view is not None and hasattr(view, "activate_child"):
            view.activate_child()

    def search_prev(self, text):
        view = self.get_visible_child()
        if view is not None and hasattr(view, "search_prev"):
            view.search_prev(text)

    def search_next(self, text):
        view = self.get_visible_child()
        if view is not None and hasattr(view, "search_next"):
            view.search_next(text)


class Container(Gtk.Overlay, NotificationContainer,
                ScannerContainer, PlaylistsContainer,
                ListsContainer, ViewsContainer, FilterContainer):
    """
        Main view management
    """

    def __init__(self):
        """
            Init container
            @param view_type as ViewType, will be appended to any created view
        """
        Gtk.Overlay.__init__(self)
        NotificationContainer.__init__(self)
        ScannerContainer.__init__(self)
        PlaylistsContainer.__init__(self)
        ViewsContainer.__init__(self)
        self._sidebar_one = None
        self._sidebar_two = None
        self.__paned_position_id = None
        self._stack = ContainerStack()
        self._stack.connect("visible-child-changed",
                            self.__on_visible_child_changed)
        self._stack.show()
        self.__progress = ProgressBar()
        self.__progress.get_style_context().add_class("progress-bottom")
        self.__progress.set_property("valign", Gtk.Align.END)
        self.add_overlay(self.__progress)
        search_action = App().lookup_action("search")
        search_action.connect("activate", self.__on_search_activate)
        self._sidebar_one = Gtk.Grid()
        self._sidebar_two = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self._sidebar_two.connect("notify::position", self.__on_paned_position)
        self._sidebar_two.add2(self._stack)
        self._sidebar_one.attach(self._sidebar_two, 0, 0, 1, 1)
        position = App().settings.get_value(
            "paned-listview-width").get_int32()
        self._sidebar_two.set_position(position)
        self._sidebar_one.show()
        self._sidebar_two.show()
        self._grid = Gtk.Grid()
        self._grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._grid.set_column_spacing(2)
        self._grid.show()
        self.add(self._grid)
        FilterContainer.__init__(self)
        ListsContainer.__init__(self)

    def stop_all(self):
        """
            Stop current view from processing
        """
        view = self._stack.get_visible_child()
        if view is not None:
            view.stop()

    def reload_view(self):
        """
            Reload current view
        """
        pass

    @property
    def view(self):
        """
            Get current view
            @return View
        """
        view = self._stack.get_visible_child()
        if view is not None and isinstance(view, View):
            return view
        return None

    @property
    def stack(self):
        """
            Container stack
            @return stack as Gtk.Stack
        """
        return self._stack

    @property
    def progress(self):
        """
            Progress bar
            @return ProgressBar
        """
        return self.__progress

############
# PRIVATE  #
############
    def __show_settings_dialog(self):
        """
            Show settings dialog if view exists in stack
        """
        from lollypop.view_settings import SettingsChildView
        from lollypop.view_settings import SettingsView
        if isinstance(self.view, SettingsChildView) or\
                isinstance(self.view, SettingsView):
            action = App().lookup_action("settings")
            GLib.idle_add(action.activate,
                          GLib.Variant("i", self.view.type))

    def __on_search_activate(self, action, variant):
        """
            @param action as Gio.SimpleAction
            @param variant as GLib.Variant
        """
        if App().window.is_adaptive:
            search = variant.get_string()
            App().window.container.show_view([Type.SEARCH], search)

    def __on_visible_child_changed(self, stack, sidebar_id):
        """
            Active sidebar selected id
            @param stack as ContainerStack
            @param sidebar_id as int
        """
        self._sidebar.select_ids([sidebar_id], False)

    def __on_paned_position(self, paned, param):
        """
            Save paned position
            @param paned as Gtk.Paned
            @param param as GParamSpec
        """
        def save_position():
            self.__paned_position_id = None
            position = paned.get_property(param.name)
            # We do not want to save position while adaptive mode is set
            if App().window is not None and App().window.is_adaptive:
                return
            App().settings.set_value("paned-listview-width",
                                     GLib.Variant("i",
                                                  position))
        # We delay position saving
        # Useful for adative mode where position get garbaged
        if self.__paned_position_id is not None:
            GLib.source_remove(self.__paned_position_id)
        self.__paned_position_id = GLib.timeout_add(
            1000, save_position)
