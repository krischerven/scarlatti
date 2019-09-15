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

from gi.repository import Gio, GObject

from lollypop.widgets_artwork import ArtworkSearchWidget, ArtworkSearchChild
from lollypop.define import App
from lollypop.logger import Logger


class RadioArtworkSearchWidget(ArtworkSearchWidget):
    """
        Search for radio artwork
    """

    __gsignals__ = {
        "hidden": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self, name, view_type):
        """
            Init search
            @param name as str
            @param view_type as ViewType
        """
        ArtworkSearchWidget.__init__(self, view_type)
        self.__name = name

#######################
# PROTECTED           #
#######################
    def _save_from_filename(self, filename):
        """
            Save filename as album artwork
            @param button as Gtk.button
        """
        try:
            f = Gio.File.new_for_path(filename)
            (status, data, tag) = f.load_contents()
            if status:
                App().art.add_radio_artwork(self.__name, data)
            App().art.clean_radio_cache(self.__name)
            App().art.radio_artwork_update(self.__name)
        except Exception as e:
            Logger.error(
                "RadioArtworkSearchWidget::_save_from_filename(): %s" % e)

    def _get_current_search(self):
        """
            Return current searches
            @return str
        """
        search = ArtworkSearchWidget._get_current_search(self)
        if search != "":
            pass
        else:
            search = self.__name
        return search

    def _on_activate(self, flowbox, child):
        """
            Save artwork
            @param flowbox as Gtk.FlowBox
            @param child as ArtworkSearchChild
        """
        try:
            if isinstance(child, ArtworkSearchChild):
                App().task_helper.run(App().art.add_radio_artwork,
                                      self.__name, child.bytes)
            else:
                App().task_helper.run(App().art.add_radio_artwork,
                                      self.__name, None)
            self.emit("hidden", True)
        except Exception as e:
            Logger.error("RadioArtworkSearchWidget::_on_activate(): %s", e)
