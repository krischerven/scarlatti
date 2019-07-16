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
from lollypop.define import App, LOLLYPOP_DATA_PATH


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
        self.__history = []

    def add_view(self, view):
        """
            Add view to history
            Offload old views
            @param view as View
        """
        if view.args is not None:
            self.__history.append((view, view.__class__, view.args))
        if self.count >= self.__MAX_HISTORY_ITEMS:
            (view, _class, args) = self.__history[-self.__MAX_HISTORY_ITEMS]
            if view is not None and view.should_destroy:
                view.destroy()
                self.__history[
                    -self.__MAX_HISTORY_ITEMS] = (None, _class, args)

    def pop(self, index=-1):
        """
            Pop last view from history
            @param index as int
            @return view
        """
        if not self.__history:
            return None
        (view, _class, args) = self.__history.pop(index)
        try:
            # Here, we are restoring an offloaded view
            if view is None:
                view = _class(**args[0])
                # Restore scrolled position
                # For LazyLoadingView, we can't restore this too soon
                if hasattr(view, "_scrolled"):
                    if hasattr(view, "_on_populated"):
                        view.set_populated_scrolled_position(args[3])
                    else:
                        adj = view._scrolled.get_vadjustment()
                        GLib.idle_add(adj.set_value, args[3])
                # Start populating the view
                if hasattr(view, "populate"):
                    view.populate(**args[1])
                view.show()
            App().window.container.sidebar.select_ids([args[2]], False)
            return view
        except Exception as e:
            Logger.warning("AdaptiveHistory::pop(): %s, %s", _class, e)

    def search(self, view_class, view_args):
        """
            Search view with class and args
            @param view_class as class
            @param view_args as {}
            @return View
        """
        index = 0
        found = False
        for (_view, _class, args) in self.__history:
            if _class == view_class and args[0] == view_args:
                found = True
                break
            index += 1
        if found:
            view = self.pop(index)
            return view
        return None

    def remove(self, view):
        """
            Remove view from history
            @param view as View
        """
        for (_view, _class, args) in self.__history:
            if _view == view:
                self.__history.remove((_view, _class, args))
                break

    def reset(self):
        """
            Reset history
        """
        for (view, _class, args) in self.__history:
            if view is not None:
                view.stop()
                view.destroy_later()
        self.__history = []

    def save(self):
        """
            Save history
        """
        try:
            no_widget_history = []
            for (_view, _class, args) in self.__history[
                                                   -self.__MAX_HISTORY_ITEMS:]:
                no_widget_history.append((None, _class, args))
            with open(LOLLYPOP_DATA_PATH + "/history.bin", "wb") as f:
                dump(list(no_widget_history), f)
        except Exception as e:
            Logger.error("Application::__save_state(): %s" % e)

    def load(self):
        """
            Load history
        """
        try:
            self.__history = load(
                open(LOLLYPOP_DATA_PATH + "/history.bin", "rb"))
        except Exception as e:
            Logger.error("Application::__save_state(): %s" % e)

    def exists(self, view):
        """
            True if view exists in history
            @return bool
        """
        for (_view, _class, args) in self.__history:
            if _view == view:
                return True
        return False

    @property
    def count(self):
        """
            Get history item count
            @return int
        """
        return len(self.__history)


class AdaptiveStack(Gtk.Stack):
    """
        A Gtk.Stack handling navigation
    """

    __gsignals__ = {
        "new-child-in-history": (GObject.SignalFlags.RUN_FIRST, None, ()),
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

    def add(self, widget):
        """
            Add widget to stack
            @param widget as Gtk.Widget
        """
        if widget not in self.get_children():
            Gtk.Stack.add(self, widget)

    def set_visible_child(self, widget):
        """
            Set visible child in stack
            @param widget as Gtk.Widget
        """
        visible_child = self.get_visible_child()
        if visible_child == widget:
            return
        if visible_child is not None:
            self.__history.add_view(visible_child)
            self.emit("new-child-in-history")
            visible_child.stop()
            if visible_child.args is None:
                visible_child.destroy_later()
        Gtk.Stack.set_visible_child(self, widget)

    def go_back(self):
        """
            Go back in stack
        """
        if self.__history:
            visible_child = self.get_visible_child()
            widget = self.__history.pop()
            if widget is None:
                return
            if widget not in self.get_children():
                self.add(widget)
            Gtk.Stack.set_visible_child(self, widget)
            if visible_child is not None:
                visible_child.stop()
                visible_child.destroy_later()

    def remove(self, widget):
        """
            Remove from stack and history
            @param widget as Gtk.Widget
        """
        if self.__history.exists(widget):
            self.__history.remove(widget)
        Gtk.Stack.remove(self, widget)

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
        self.__history.load()
        view = self.__history.pop()
        if view is not None:
            self.add(view)
            self.set_visible_child(view)

    @property
    def history(self):
        """
            Get stack history
            @return [AdaptiveView]
        """
        return self.__history

############
# PRIVATE  #
############
    def __on_child_destroy(self, widget):
        """
            Remove from history
            @param widget as Gtk.Widget
        """
        if self.__history.exists(widget):
            self.__history.remove(widget)


class AdaptiveWindow:
    """
        Handle window resizing and window's children workflow
        This class needs a stack and n paned
    """
    _ADAPTIVE_STACK = 600

    gsignals = {
        "adaptive-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
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
        self.__configure_event_connected = False
        self.__adaptive_timeout_id = None
        self.__stack = None
        self.__children = []

    def set_stack(self, stack):
        """
            Add stack to adaptive mode
            @param stack as AdaptiveStack
        """
        self.__stack = stack
        self.__stack.connect("new-child-in-history",
                             self.__on_new_child_in_history)

    def add_adaptive_child(self, parent, child):
        """
            Add an adaptive child
            @param parent as Gtk.Container
            @param child as Gtk.Widget
        """
        self.__children.append((parent, child))
        child.connect("destroy", self.__on_child_destroy)

    def go_back(self):
        """
            Go back in container stack
        """
        self.__stack.go_back()
        self.emit("can-go-back-changed", self.__stack.history.count > 0)

    def go_home(self):
        """
            Go back to first page
        """
        if self.__stack.history.count > 0:
            widget = self.__stack.history.pop(0)
            self.__stack.history.reset()
            self.__stack.set_visible_child(widget)
            self.emit("can-go-back-changed", False)

    def set_adaptive_stack(self, b):
        """
            Move paned child to stack
            @param b as bool
        """
        # Do adaptive on init
        if self._adaptive_stack is None:
            self._adaptive_stack = not b
        if b == self._adaptive_stack:
            return
        if self.__adaptive_timeout_id is not None:
            GLib.source_remove(self.__adaptive_timeout_id)
        self.__adaptive_timeout_id = GLib.idle_add(
            self.__set_adaptive_stack, b)

    def do_adaptive_mode(self, width):
        """
            Handle basic adaptive mode
            Will start to listen to configure event
            @param width as int
        """
        def connect_configure_event():
            self.connect("configure-event", self.__on_configure_event)

        if width < self._ADAPTIVE_STACK:
            self.set_adaptive_stack(True)
        else:
            self.set_adaptive_stack(False)
        # We delay connect to ignore initial configure events
        if not self.__configure_event_connected:
            self.__configure_event_connected = True
            GLib.timeout_add(1000, connect_configure_event)

    @property
    def can_go_back(self):
        """
            True if can go back
            @return bool
        """
        return self.__stack.history.count > 0

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

    def __set_adaptive_stack(self, b):
        """
            Handle adaptive switch
            @param b as bool
        """
        self.__adaptive_timeout_id = None
        self.__update_layout(b)
        self.emit("adaptive-changed", b)

    def __on_new_child_in_history(self, stack):
        """
            Emit can-go-back-changed if can go back
        """
        if self.can_go_back:
            self.emit("can-go-back-changed", True)

    def __on_child_destroy(self, widget):
        """
            Remove widget from paned
            @param widget as Gtk.Widget
        """
        # FIXME needed?
        for (p, c) in self.__children:
            if c == widget:
                self.__children.remove((p, c))
                break

    def __on_configure_event(self, widget, event):
        """
            Delay event
            @param widget as Gtk.Window
            @param event as Gdk.EventConfigure
        """
        self.do_adaptive_mode(widget.get_size()[0])
