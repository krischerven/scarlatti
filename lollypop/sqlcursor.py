# Copyright (c) 2017-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from threading import current_thread
from time import sleep

from lollypop.define import App


class SqlCursor:
    """
        Context manager to get the SQL cursor
    """
    def add(obj):
        """
            Add cursor to thread list
        """
        obj.thread_lock.acquire()
        name = current_thread().getName() + obj.__class__.__name__
        App().cursors[name] = obj.get_cursor()

    def remove(obj):
        """
            Remove cursor from thread list and commit
        """
        name = current_thread().getName() + obj.__class__.__name__
        if name in App().cursors.keys():
            App().cursors[name].commit()
            App().cursors[name].close()
            del App().cursors[name]
        obj.thread_lock.release()

    def commit(obj):
        """
            Commit current obj
        """
        name = current_thread().getName() + obj.__class__.__name__
        if name in App().cursors.keys():
            App().cursors[name].commit()

    def allow_thread_execution(obj):
        """
            Release thread lock allowing others threads execution
        """
        name = current_thread().getName() + obj.__class__.__name__
        if name in App().cursors.keys() and obj.thread_lock.count > 1:
            App().cursors[name].commit()
            obj.thread_lock.release()
            sleep(0.000001)
            obj.thread_lock.acquire()

    def __init__(self, obj, commit=False):
        """
            Init object, if using multiple SqlCursor, parent commit param will
            be used
            @param obj as Database/Playlists/Radios
            @param commit as bool
        """
        self.__obj = obj
        self.__creator = False
        self.__commit = commit

    def __enter__(self):
        """
            Return cursor for thread, create a new one if needed
        """
        name = current_thread().getName() + self.__obj.__class__.__name__
        if name not in App().cursors.keys():
            App().cursors[name] = self.__obj.get_cursor()
            self.__creator = True
            if self.__commit:
                self.__obj.thread_lock.acquire()
        return App().cursors[name]

    def __exit__(self, type, value, traceback):
        """
            If creator, close cursor and remove it
        """
        name = current_thread().getName() + self.__obj.__class__.__name__
        if name in App().cursors.keys() and self.__creator:
            if self.__commit:
                App().cursors[name].commit()
                self.__obj.thread_lock.release()
            App().cursors[name].close()
            del App().cursors[name]
