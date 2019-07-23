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

from functools import wraps

from lollypop.define import App
from lollypop.logger import Logger
# For lint
App()


def signals(f):
    """
        Decorator to init signal helper
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        ret = f(*args, **kwargs)
        SignalsHelper.__init__(args[0])
        args[0].init(ret)

    return wrapper


def signals_map(f):
    """
        Decorator to init signal helper
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        ret = f(*args, **kwargs)
        SignalsHelper.__init__(args[0])
        args[0].init_map(ret)

    return wrapper


class SignalsHelper():
    """
        Helper for autoconnect/disconnect signals on map
    """

    def __init__(self):
        """
            Init helper
        """
        if not hasattr(self, "_connected"):
            self._connected = []

    def init(self, signals):
        """
            Init signals
        """
        if signals:
            self._connect_signals(signals)
            self.connect("destroy",
                         lambda x: self._disconnect_signals(signals))

    def init_map(self, signals):
        """
            Init map signals
        """
        if signals:
            self.connect("map",
                         lambda x: self._connect_signals(signals))
            self.connect("unmap",
                         lambda x: self._disconnect_signals(signals))

#######################
# PROTECTE            #
#######################
    def _connect_signals(self, signals):
        """
            Connect signals
            @param signals as []
        """
        for (obj, signal, callback_str) in signals:
            if obj is None:
                Logger.warning("Can't connect signal: %s", signal)
                continue
            name = "%s_%s" % (obj, signal)
            if name in self._connected:
                continue
            if isinstance(obj, str):
                obj = eval(obj)
            callback = getattr(self, callback_str)
            obj.connect(signal, callback)
            self._connected.append(name)

    def _disconnect_signals(self, signals):
        """
            Disconnect signals
            @param signals as []
        """
        for (obj, signal, callback_str) in signals:
            if obj is None:
                Logger.warning("Can't disconnect signal: %s", signal)
                continue
            name = "%s_%s" % (obj, signal)
            if name not in self._connected:
                continue
            if isinstance(obj, str):
                obj = eval(obj)
            callback = getattr(self, callback_str)
            obj.disconnect_by_func(callback)
            self._connected.remove(name)
