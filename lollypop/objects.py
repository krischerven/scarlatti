# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2015 Jean-Philippe Braun <eon@patapon.info>
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

from lollypop.radios import Radios
from lollypop.logger import Logger
from lollypop.define import App, Type
from lollypop.utils import emit_signal


class Base:
    """
        Base for album and track objects
    """

    def __init__(self, db):
        self.db = db

    def __dir__(self, *args, **kwargs):
        """
            Concatenate base class"s fields with child class"s fields
        """
        return super(Base, self).__dir__(*args, **kwargs) +\
            list(self.DEFAULTS.keys())

    # Used by pickle
    def __getstate__(self): return self.__dict__

    def __setstate__(self, d): self.__dict__.update(d)

    def __getattr__(self, attr):
        # Lazy DB calls of attributes
        if attr in list(self.DEFAULTS.keys()):
            if self.id is None or self.id < 0:
                return self.DEFAULTS[attr]
            # Actual value of "attr_name" is stored in "_attr_name"
            attr_name = "_" + attr
            attr_value = getattr(self, attr_name)
            if attr_value is None:
                attr_value = getattr(self.db, "get_" + attr)(self.id)
                setattr(self, attr_name, attr_value)
            # Return default value if None
            if attr_value is None:
                return self.DEFAULTS[attr]
            else:
                return attr_value

    def reset(self, attr):
        """
            Reset attr
            @param attr as str
        """
        attr_name = "_" + attr
        attr_value = getattr(self.db, "get_" + attr)(self.id)
        setattr(self, attr_name, attr_value)

    def get_popularity(self):
        """
            Get popularity
            @return int between 0 and 5
        """
        if self.id is None:
            return 0

        popularity = 0
        if self.id >= 0:
            avg_popularity = self.db.get_avg_popularity()
            if avg_popularity > 0:
                popularity = self.db.get_popularity(self.id)
        elif self.id == Type.RADIOS:
            radios = Radios()
            avg_popularity = radios.get_avg_popularity()
            if avg_popularity > 0:
                popularity = radios.get_popularity(self._radio_id)
        return popularity * 5 / avg_popularity + 0.5

    def set_popularity(self, new_rate):
        """
            Set popularity
            @param new_rate as int between 0 and 5
        """
        if self.id is None:
            return
        try:
            if self.id >= 0:
                avg_popularity = self.db.get_avg_popularity()
                popularity = int((new_rate * avg_popularity / 5) + 0.5)
                best_popularity = self.db.get_higher_popularity()
                if new_rate == 5:
                    popularity = (popularity + best_popularity) / 2
                self.db.set_popularity(self.id, popularity)
            elif self.id == Type.RADIOS:
                radios = Radios()
                avg_popularity = radios.get_avg_popularity()
                popularity = int((new_rate * avg_popularity / 5) + 0.5)
                best_popularity = self.db.get_higher_popularity()
                if new_rate == 5:
                    popularity = (popularity + best_popularity) / 2
                radios.set_popularity(self._radio_id, popularity)
        except Exception as e:
            Logger.error("Base::set_popularity(): %s" % e)

    def get_rate(self):
        """
            Get rate
            @return int
        """
        if self.id is None:
            return 0

        rate = 0
        if self.id >= 0:
            rate = self.db.get_rate(self.id)
        elif self.id == Type.RADIOS:
            radios = Radios()
            rate = radios.get_rate(self._radio_id)
        return rate

    def set_rate(self, rate):
        """
            Set rate
            @param rate as int between -1 and 5
        """
        if self.id == Type.RADIOS:
            radios = Radios()
            radios.set_rate(self._radio_id, rate)
            emit_signal(App().player, "rate-changed", self._radio_id, rate)
        else:
            self.db.set_rate(self.id, rate)
            emit_signal(App().player, "rate-changed", self.id, rate)
