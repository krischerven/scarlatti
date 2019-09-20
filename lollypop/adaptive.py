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

from gi.repository import GObject, Gtk, GLib

from pickle import dump, load

from lollypop.logger import Logger
from lollypop.define import LOLLYPOP_DATA_PATH, AdaptiveSize, Size


class AdaptiveView:
    """
        AdaptiveStack children
    """

    def __init__(self):
        """
            Init view
        """
        self.__sidebar_id = None
        self.__selection_ids = {"left": [], "right": []}

    def set_sidebar_id(self, sidebar_id):
        """
            Set sidebar id
            @param sidebar_id as int
        """
        self.__sidebar_id = sidebar_id

    def set_selection_ids(self, selection_ids):
        """
            Set selection ids
            @param selection_ids as {"left": [int], "right": [int])
        """
        self.__selection_ids = selection_ids

    def destroy_later(self):
        """
            Delayed destroy
            Allow animations in stack
        """
        def do_destroy():
            self.destroy()
        self.stop()
        if self.args is not None:
            GLib.timeout_add(1000, do_destroy)

    @property
    def sidebar_id(self):
        """te
            Get sidebar id
            @return int
        """
        return self.__sidebar_id

    @property
    def selection_ids(self):
        """
            Get selection ids (sidebar id + extra ids)
            return [int]
        """
        return self.__selection_ids

    @property
    def args(self):
        """
            Get default args for __class__
            @return {}
        """
        return {}


class AdaptiveHistory:
    """
        Navigation history
        Offload old items and reload them on the fly
    """

    __MAX_HISTORY_ITEMS = 10

    def __init__(self):
        """
            Init history
        """
        self.__items = []

    def add_view(self, view):
        """
            Add view to history
            @param view as View
        """
        view_class = view.__class__
        self.__items.append((view, view_class, view.args, view.sidebar_id,
                             view.selection_ids, view.position))
        # Offload history if too many items
        if self.count >= self.__MAX_HISTORY_ITEMS:
            (view, _class, args, sidebar_id,
             selection_ids, position) = self.__items[-self.__MAX_HISTORY_ITEMS]
            if view is not None:
                view.destroy()
                # This view can't be offloaded
                if args is None:
                    del self.__items[-self.__MAX_HISTORY_ITEMS]
                else:
                    self.__items[-self.__MAX_HISTORY_ITEMS] =\
                        (None, _class, args, sidebar_id,
                         selection_ids, position)

    def pop(self, index=-1):
        """
            Pop last view from history
            @param index as int
            @return View
        """
        try:
            if not self.__items:
                return None
            (view, _class, args, sidebar_id,
             selection_ids, position) = self.__items.pop(index)
            # View is offloaded, create a new one
            if view is None:
                view = self.__get_view_from_class(_class, args)
                view.set_sidebar_id(sidebar_id)
                view.set_selection_ids(selection_ids)
                view.set_populated_scrolled_position(position)
            return view
        except Exception as e:
            Logger.error("AdaptiveHistory::pop(): %s" % e)
            self.__items = []

    def remove(self, view):
        """
            Remove view from history
            @param view as View
        """
        for (_view, _class, args, sidebar_id,
             selection_ids, position) in self.__items:
            if _view == view:
                self.__items.remove((_view, _class, args, sidebar_id,
                                     selection_ids, position))
                break

    def reset(self):
        """
            Reset history
        """
        for (view, _class, args, sidebar_id,
             selection_ids, position) in self.__items:
            if view is not None:
                view.stop()
                view.destroy_later()
        self.__items = []

    def save(self):
        """
            Save history
        """
        try:
            history = []
            for (_view, _class, args, sidebar_id,
                 selection_ids, position) in self.__items[-50:]:
                history.append((None, _class, args, sidebar_id,
                                selection_ids, position))
            with open(LOLLYPOP_DATA_PATH + "/history.bin", "wb") as f:
                dump(history, f)
        except Exception as e:
            Logger.error("AdaptiveHistory::save(): %s" % e)

    def load(self):
        """
            Load history
        """
        try:
            self.__items = load(
                open(LOLLYPOP_DATA_PATH + "/history.bin", "rb"))
        except Exception as e:
            Logger.error("AdaptiveHistory::load(): %s" % e)

    def exists(self, view):
        """
            True if view exists in history
            @return bool
        """
        for (_view, _class, args, sidebar_id,
             selection_ids, position) in self.__items:
            if _view == view:
                return True
        return False

    @property
    def items(self):
        """
            Get history items
            @return [(View, class, {})]
        """
        return self.__items

    @property
    def count(self):
        """
            Get history item count
            @return int
        """
        return len(self.__items)

############
# PRIVATE  #
############
    def __get_view_from_class(self, _class, args):
        """
            Get view from history
            @param _class as class
            @param args as {}
            @return View
        """
        try:
            view = _class(**args)
            # Start populating the view
            if hasattr(view, "populate"):
                view.populate()
            view.show()
            return view
        except Exception as e:
            Logger.warning(
                "AdaptiveHistory::__get_view_from_class(): %s, %s",
                _class, e)
        return None


class AdaptiveStack(Gtk.Stack):
    """
        A Gtk.Stack handling navigation
    """

    __gsignals__ = {
        "history-changed":   (GObject.SignalFlags.RUN_FIRST, None, ()),
        "set-sidebar-id":    (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "set-selection-ids": (GObject.SignalFlags.RUN_FIRST, None,
                              (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self):
        """
            Init stack
            @param window as AdaptiveWindow
        """
        Gtk.Stack.__init__(self)
        self.set_transition_duration(300)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.__history = AdaptiveHistory()

    def add(self, view):
        """
            Add view to stack
            @param view as View
        """
        if view not in self.get_children():
            Gtk.Stack.add(self, view)

    def set_visible_child(self, view):
        """
            Set visible child in stack
            @param view as View
        """
        visible_child = self.get_visible_child()
        if visible_child != view:
            if visible_child is not None:
                visible_child.pause()
                self.__history.add_view(visible_child)
                Gtk.Stack.set_visible_child(self, view)
                self.emit("history-changed")
            else:
                Gtk.Stack.set_visible_child(self, view)

    def go_back(self):
        """
            Go back in stack
        """
        if self.__history:
            visible_child = self.get_visible_child()
            view = self.__history.pop()
            if view is not None:
                if view not in self.get_children():
                    self.add(view)
                Gtk.Stack.set_visible_child(self, view)
                self.emit("set-sidebar-id", view.sidebar_id)
                self.emit("set-selection-ids", view.selection_ids)
                if visible_child is not None:
                    visible_child.stop()
                    visible_child.destroy_later()

    def remove(self, view):
        """
            Remove from stack and history
            @param view as View
        """
        if self.__history.exists(view):
            self.__history.remove(view)
        Gtk.Stack.remove(self, view)

    def save_history(self):
        """
            Save history to disk
        """
        visible_child = self.get_visible_child()
        if visible_child is not None:
            self.__history.add_view(visible_child)
        self.__history.save()

    def load_history(self):
        """
            Load history from disk
        """
        try:
            self.__history.load()
            view = self.__history.pop()
            if view is not None:
                self.add(view)
                Gtk.Stack.set_visible_child(self, view)
                self.emit("set-sidebar-id", view.sidebar_id)
                self.emit("set-selection-ids", view.selection_ids)
        except Exception as e:
            Logger.error("AdaptiveStack::load_history(): %s", e)

    @property
    def history(self):
        """
            Get stack history
            @return [AdaptiveView]
        """
        return self.__history


class AdaptiveWindow:
    """
        Handle window resizing and window's children workflow
        This class needs a stack and n paned
    """

    gsignals = {
        "adaptive-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "adaptive-size-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }
    for signal in gsignals:
        args = gsignals[signal]
        GObject.signal_new(signal, Gtk.Window,
                           args[0], args[1], args[2])

    def __init__(self):
        """
            Init adaptive mode, Gtk.Window should be initialised
        """
        self.__is_adaptive = None
        self.__configure_timeout_id = None
        self.__adaptive_size = AdaptiveSize.NONE
        self.connect("configure-event", self.__on_configure_event)

    def set_adaptive(self, is_adaptive):
        """
            Handle adaptive switch
            @param is_adaptive as bool
        """
        if is_adaptive != self.__is_adaptive:
            self.__is_adaptive = is_adaptive
            self.emit("adaptive-changed", is_adaptive)

    @property
    def adaptive_size(self):
        """
            Get adaptive size
            @return AdaptiveSize
        """
        return self.__adaptive_size

    @property
    def is_adaptive(self):
        """
            True if adaptive is on
            @return bool
        """
        return False if self.__is_adaptive is None else self.__is_adaptive

#############
# PROTECTED #
#############
    def _on_configure_event_timeout(self, width, height, x, y):
        """
            Handle adaptive mode
            @param width as int
            @param height as int
            @param x as int
            @param y as int
        """
        self.__configure_timeout_id = None
        if width <= Size.MEDIUM:
            self.set_adaptive(True)
        else:
            self.set_adaptive(False)
        if width <= Size.SMALL:
            adaptive_size = AdaptiveSize.SMALL
        elif width <= Size.MEDIUM:
            adaptive_size = AdaptiveSize.MEDIUM
        elif width <= Size.NORMAL:
            adaptive_size = AdaptiveSize.NORMAL
        elif width <= Size.BIG:
            adaptive_size = AdaptiveSize.BIG
        else:
            adaptive_size = AdaptiveSize.LARGE
        if adaptive_size != self.__adaptive_size:
            self.__adaptive_size = adaptive_size
            self.emit("adaptive-size-changed", adaptive_size)

############
# PRIVATE  #
############
    def __on_configure_event(self, window, event):
        """
            Delay event
            @param window as Gtk.Window
            @param event as Gdk.EventConfigure
        """
        if self.__configure_timeout_id:
            GLib.source_remove(self.__configure_timeout_id)
        (width, height) = window.get_size()
        (x, y) = window.get_position()
        self.__configure_timeout_id = GLib.idle_add(
            self._on_configure_event_timeout,
            width, height, x, y, priority=GLib.PRIORITY_LOW)
