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
        pass

    def destroy_later(self):
        """
            Delayed destroy
            Allow animations in stack
        """
        def do_destroy():
            self.destroy()
        self.stop()
        if self.should_destroy:
            GLib.timeout_add(1000, do_destroy)

    @property
    def should_destroy(self):
        """
            True if view should be destroyed
            @return bool
        """
        return True


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

    def add_view(self, view, force_offloading=False):
        """
            Add view to history
            @param view as View
            @param force_offloading as bool
            @return True if view has been added
        """
        added = False
        # Do not add unwanted view to history
        args = view.args
        if args is not None:
            view_class = view.__class__
            if force_offloading:
                view.destroy()
                view = None
            self.__items.append((view, view_class, args))
            added = True
            # Offload history if too many items
            if self.count >= self.__MAX_HISTORY_ITEMS:
                (view, _class, args) = self.__items[-self.__MAX_HISTORY_ITEMS]
                if view is not None:
                    view.destroy()
                    self.__items[-self.__MAX_HISTORY_ITEMS] =\
                        (None, _class, args)
        return added

    def pop(self, index=-1):
        """
            Pop last view from history
            @param index as int
            @return (view as View, sidebar_id as int)
        """
        if not self.__items:
            return (None, None)
        (view, _class, args) = self.__items.pop(index)
        # Undestroyable view (sidebar, list_view)
        if view is not None:
            return (view, args[1])
        else:
            return self.__get_view_from_class(view, _class, args)

    def remove(self, view):
        """
            Remove view from history
            @param view as View
        """
        for (_view, _class, args) in self.__items:
            if _view == view:
                self.__items.remove((_view, _class, args))
                break

    def reset(self):
        """
            Reset history
        """
        for (view, _class, args) in self.__items:
            if view is not None:
                view.stop()
                view.destroy_later()
        self.__items = []

    def save(self):
        """
            Save history
        """
        try:
            no_widget_history = []
            for (_view, _class, args) in self.__items[-50:]:
                if _class is not None:
                    no_widget_history.append((None, _class, args))
            with open(LOLLYPOP_DATA_PATH + "/history.bin", "wb") as f:
                dump(no_widget_history, f)
        except Exception as e:
            Logger.error("Application::__save_state(): %s" % e)

    def load(self):
        """
            Load history
        """
        try:
            self.__items = load(
                open(LOLLYPOP_DATA_PATH + "/history.bin", "rb"))
        except Exception as e:
            Logger.error("Application::__save_state(): %s" % e)

    def exists(self, view):
        """
            True if view exists in history
            @return bool
        """
        for (_view, _class, args) in self.__items:
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
    def __get_view_from_class(self, view, _class, args):
        """
            Get view from history
            @param view as View
            @param _class as class
            @param args as {}
            @return (View, sidebar_id)
        """
        try:
            # Here, we are restoring an offloaded view
            if view is None:
                view = _class(**args[0])
                # Restore scrolled position
                # For LazyLoadingView, we can't restore this too soon
                if hasattr(view, "_scrolled"):
                    if hasattr(view, "_on_populated"):
                        view.set_populated_scrolled_position(args[2])
                    else:
                        adj = view._scrolled.get_vadjustment()
                        GLib.idle_add(adj.set_value, args[2])
                # Start populating the view
                if hasattr(view, "populate"):
                    view.populate()
                view.show()
            return (view, args[1])
        except Exception as e:
            Logger.warning(
                "AdaptiveHistory::__get_view_from_class(): %s, %s",
                _class, e)
        return (None, None)


class AdaptiveStack(Gtk.Stack):
    """
        A Gtk.Stack handling navigation
    """

    __gsignals__ = {
        "history-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "visible-child-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
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
        if visible_child == view:
            return
        if visible_child is not None:
            visible_child.stop()
            added = self.__history.add_view(visible_child)
            if added:
                self.emit("history-changed")
            else:
                visible_child.destroy_later()
        Gtk.Stack.set_visible_child(self, view)

    def go_back(self):
        """
            Go back in stack
        """
        if self.__history:
            visible_child = self.get_visible_child()
            (view, sidebar_id) = self.__history.pop()
            if view is not None:
                if view not in self.get_children():
                    self.add(view)
                Gtk.Stack.set_visible_child(self, view)
                self.emit("visible-child-changed", sidebar_id)
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
            (view, sidebar_id) = self.__history.pop()
            if view is not None:
                self.add(view)
                Gtk.Stack.set_visible_child(self, view)
                self.emit("visible-child-changed", sidebar_id)
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
        "can-go-back-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }
    for signal in gsignals:
        args = gsignals[signal]
        GObject.signal_new(signal, Gtk.Window,
                           args[0], args[1], args[2])

    def __init__(self):
        """
            Init adaptive mode, Gtk.Window should be initialised
        """
        self._adaptive_stack = None
        self.__stack = None
        self.__children = []
        self.__configure_timeout_id = None
        self.__adaptive_size = AdaptiveSize.NONE
        self.connect("configure-event", self.__on_configure_event)

    def set_stack(self, stack):
        """
            Add stack to adaptive mode
            @param stack as AdaptiveStack
        """
        self.__stack = stack
        self.__stack.connect("history-changed",
                             self.__on_history_changed)

    def add_adaptive_child(self, parent, child):
        """
            Add an adaptive child
            @param parent as Gtk.Container
            @param child as Gtk.Widget
        """
        self.__children.append((parent, child))

    def go_back(self):
        """
            Go back in container stack
        """
        if self.__stack.history.count > 0:
            self.__stack.go_back()
        elif self.is_adaptive:
            visible_child = self.__stack.get_visible_child()
            for child in reversed(self.__children):
                if child[1] == visible_child:
                    visible_child = None
                elif child[1].get_visible():
                    Gtk.Stack.set_visible_child(self.__stack, child[1])
                    break
            if visible_child is not None:
                visible_child.destroy_later()
        self.emit("can-go-back-changed", self.can_go_back)

    def go_home(self):
        """
            Go back to first page
        """
        view = self.__children[0][1]
        self.__stack.set_visible_child(view)
        self.__stack.history.reset()
        self.emit("can-go-back-changed", False)

    def set_adaptive_stack(self, b):
        """
            Move paned child to stack
            @param b as bool
        """
        if b == self._adaptive_stack:
            return
        self.__set_adaptive_stack(b)

    @property
    def can_go_back(self):
        """
            True if can go back
            @return bool
        """
        if self.is_adaptive:
            return self.__stack.get_visible_child() != self.__children[0][1]
        else:
            return self.__stack.history.count > 0

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
        return self._adaptive_stack is True

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
        if width < Size.MEDIUM:
            self.set_adaptive_stack(True)
        else:
            self.set_adaptive_stack(False)
        if width < Size.SMALL:
            adaptive_size = AdaptiveSize.SMALL
        elif width < Size.MEDIUM:
            adaptive_size = AdaptiveSize.MEDIUM
        elif width < Size.NORMAL:
            adaptive_size = AdaptiveSize.NORMAL
        elif width < Size.BIG:
            adaptive_size = AdaptiveSize.BIG
        else:
            adaptive_size = AdaptiveSize.LARGE
        if adaptive_size != self.__adaptive_size:
            self.__adaptive_size = adaptive_size
            self.emit("adaptive-size-changed", adaptive_size)

############
# PRIVATE  #
############
    def __update_layout(self, adaptive_stack):
        """
            Update internal layout
            @param adaptive_mode as bool
        """
        self._adaptive_stack = adaptive_stack
        if not self.__children:
            return
        if adaptive_stack:
            self.__stack.set_transition_type(Gtk.StackTransitionType.NONE)
            children = self.__stack.get_children()
            for child in children:
                self.__stack.remove(child)
            for (p, c) in self.__children:
                p.remove(c)
                self.__stack.add(c)
                if c.get_visible():
                    self.__stack.set_visible_child(c)
            for child in children:
                self.__stack.add(child)
                self.__stack.set_visible_child(child)
            self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        else:
            self.__stack.set_transition_type(Gtk.StackTransitionType.NONE)
            for (p, c) in self.__children:
                self.__stack.remove(c)
                if isinstance(p, Gtk.Paned):
                    p.pack1(c, False, False)
                else:
                    p.insert_column(0)
                    p.attach(c, 0, 0, 1, 1)
            self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.emit("can-go-back-changed", self.can_go_back)

    def __set_adaptive_stack(self, b):
        """
            Handle adaptive switch
            @param b as bool
        """
        self.__adaptive_timeout_id = None
        self.__update_layout(b)
        self.emit("adaptive-changed", b)

    def __on_history_changed(self, stack):
        """
            Emit can-go-back-changed if can go back
            @param stack as Gtk.Stack
        """
        if self.can_go_back:
            self.emit("can-go-back-changed", True)

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
