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

from lollypop.define import App
from lollypop.controller_playback import PlaybackController


class ToolbarPlayback(Gtk.Bin, PlaybackController):
    """
        Playback toolbar
    """

    def __init__(self, window):
        """
            Init toolbar
            @parma window as Window
        """
        Gtk.Bin.__init__(self)
        PlaybackController.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarPlayback.ui")
        builder.connect_signals(self)

        self.add(builder.get_object("playback"))

        self._prev_button = builder.get_object("previous_button")
        self._play_button = builder.get_object("play_button")
        self._next_button = builder.get_object("next_button")
        self.__back_button = builder.get_object("back_button")
        self._play_image = builder.get_object("play_image")
        self._pause_image = builder.get_object("pause_image")
        self.__buttons = builder.get_object("buttons")

        window.connect("can-go-back-changed", self.__on_can_go_back_changed)

    def set_mini(self, mini):
        """
            Show/hide
            @param mini as bool
        """
        if mini:
            self.__buttons.hide()
        else:
            self.__buttons.show()

    @property
    def seek_wanted(self):
        """
            True if previous is about seeking at beginning
            @return bool
        """
        return self._prev_button.get_image().get_icon_name()[0] ==\
            "media-seek-backward-symbolic"

#######################
# Protected           #
#######################
    def _on_back_btn_clicked(self, button):
        """
            Go back in container stack
            @param button as Gtk.Button
        """
        App().window.go_back()

#######################
# Private             #
#######################
    def __on_show_can_go_back(self, window, back):
        """
            Show back button
            @param window as Gtk.Window
            @param back as bool
        """
        if back:
            self.__back_button.show()
        else:
            self.__back_button.hide()

    def __on_can_go_back_changed(self, window, back):
        """
            Make button sensitive
            @param window as Gtk.Window
            @param back as bool
        """
        if back:
            self.__back_button.set_sensitive(True)
        else:
            self.__back_button.set_sensitive(False)
