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

from gi.repository import Gio, GLib

from scarlatti.logger import Logger


class Settings(Gio.Settings):
    """
        Scarlatti settings
    """

    def __init__(self):
        """
            Init settings
        """
        Gio.Settings.__init__(self)

    def new():
        """
            Return a new Settings object
        """
        settings = Gio.Settings.new("org.scarlatti.Scarlatti")
        settings.__class__ = Settings
        return settings

    def reset_all_settings(settings):
        """
            Reset all settings to defaults.
        """
        for key in settings.list_keys():
            settings.reset(key)

    def get_music_uris(self):
        """
            Return music uris
            @return [str]
        """
        uris = self.get_value("music-uris")
        if not uris:
            filename = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            if filename:
                uris = [GLib.filename_to_uri(filename)]
            else:
                Logger.info("You need to add a music uri"
                            " to org.scarlatti.Scarlatti in dconf")
        return list(uris)
