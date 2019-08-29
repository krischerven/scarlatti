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

from gi.repository import Gtk

from lollypop.define import App, Size, AdaptiveSize, MARGIN
from lollypop.toolbar_playback import ToolbarPlayback
from lollypop.toolbar_info import ToolbarInfo
from lollypop.toolbar_title import ToolbarTitle
from lollypop.toolbar_end import ToolbarEnd
from lollypop.logger import Logger


class Toolbar(Gtk.HeaderBar):
    """
        Lollypop toolbar
    """

    def __init__(self, window):
        """
            Init toolbar
            @param window as Window
        """
        Gtk.HeaderBar.__init__(self)
        self.__width = Size.MINI
        self.set_title("Lollypop")
        self.__toolbar_playback = ToolbarPlayback(window)
        self.__toolbar_playback.show()
        self.__toolbar_info = ToolbarInfo()
        self.__toolbar_info.show()
        self.__toolbar_title = ToolbarTitle()
        self.__toolbar_title.show()
        self.__toolbar_end = ToolbarEnd(window)
        self.__toolbar_end.show()
        self.pack_start(self.__toolbar_playback)
        self.pack_start(self.__toolbar_info)
        self.set_custom_title(self.__toolbar_title)
        self.pack_end(self.__toolbar_end)
        self.set_property("spacing", MARGIN)

    def do_get_preferred_width(self):
        """
            Allow snapping for screen with width < 1400
            @return (int, int)
        """
        width = max(Size.SMALL, self.__width)
        return (Size.SMALL, width)

    def set_content_width(self, window_width):
        """
            Calculate infos/title width
            @param window_width as int
        """
        width = self.__toolbar_playback.get_preferred_width()[1]
        width += self.__toolbar_end.get_preferred_width()[1]
        window = self.get_window()
        if window is not None:
            self.__width = window.get_width()
            available = self.__width - width
            if available > 0:
                if App().window.adaptive_size & (AdaptiveSize.BIG |
                                                 AdaptiveSize.LARGE):
                    title = available / 2
                else:
                    title = available
                self.__toolbar_title.set_width(title)
                self.__toolbar_info.set_width((available - title) / 2)

    def set_mini(self, mini):
        """
            Set toolbar working when small
            @param mini as bool
        """
        self.__toolbar_playback.set_mini(mini)
        self.__toolbar_title.set_mini(mini)
        self.__toolbar_info.set_mini(mini)

    @property
    def end(self):
        """
            Return end toolbar
            @return ToolbarEnd
        """
        return self.__toolbar_end

    @property
    def info(self):
        """
            Return info toolbar
            @return ToolbarInfo
        """
        return self.__toolbar_info

    @property
    def title(self):
        """
            Return title toolbar
            @return ToolbarTitle
        """
        return self.__toolbar_title

    @property
    def playback(self):
        """
            Return playback toolbar
            @return ToolbarPlayback
        """
        return self.__toolbar_playback

#######################
# PRIVATE             #
#######################
    def __on_current_changed(self, player):
        """
            Update toolbar
            @param player as Player
        """
        Logger.debug("Toolbar::_on_current_changed()")
        if App().player.current_track.id is None:
            self.__toolbar_title.hide()
        elif not App().window.miniplayer:
            self.__toolbar_title.show()
        self.__toolbar_title.on_current_changed(player)

    def __on_status_changed(self, player):
        """
            Update buttons and progress bar
            @param player as Player
        """
        self.__toolbar_title.on_status_changed(player)
