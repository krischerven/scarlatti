# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gio

from gettext import gettext as _

from scarlatti.define import ViewType


class DecadeMenu(Gio.Menu):
    """
        Contextual menu for a decade
    """
    def __init__(self, years, view_type, header=False):
        """
            Init decade menu
            @param years as [int]
            @param view_type as ViewType
            @param header as bool
        """
        Gio.Menu.__init__(self)
        if header:
            from scarlatti.menu_header import RoundedMenuHeader
            name = "%s - %s" % (years[0], years[-1])
            artwork_name = "decade_%s" % name
            self.append_item(RoundedMenuHeader(name, artwork_name))
        if not view_type & ViewType.BANNER:
            from scarlatti.menu_playback import DecadePlaybackMenu
            self.append_section(_("Playback"), DecadePlaybackMenu(years))
