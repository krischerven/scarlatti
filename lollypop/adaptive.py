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


class AdaptiveStack(Gtk.Stack):
    """
        A Gtk.Stack handling navigation
    """

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
        self.__visible_child = None
        self.__history = []

    def add(self, widget):
        """
            Add widget to stack
            @param widget as Gtk.Widget
        """
        if widget not in self.get_children():
            Gtk.Stack.add(self, widget)
            self.__add_to_history(widget)
            widget.connect("destroy", self.__on_child_destroy)

    def reset_history(self):
        """
            Reset history
        """
        self.__history = []

    def set_visible_child(self, widget):
        """
            Set visible child in stack
            @param widget as Gtk.Widget
        """
        if widget == self.__visible_child:
            return
        if self.__visible_child is not None:
            self.__visible_child.stop()
        self.__visible_child = widget
        Gtk.Stack.set_visible_child(self, widget)
        self.__add_to_history(widget)

    def set_visible_child_name(self, widget, name):
        """
            Set visible child name in stack
            @param widget as Gtk.Widget
            @param name as str
        """
        self.__visible_child = widget
        Gtk.Stack.set_visible_child_name(self, widget, name)
        self.__add_to_history(widget)

    def remove(self, widget):
        """
            Remove from stack and history
            @param widget as Gtk.Widget
        """
        if widget in self.__history:
            self.__history.remove(widget)
        Gtk.Stack.remove(self, widget)

    def destroy_children(self):
        """
            Destroy not visible children
        """
        for child in self.get_children():
            child.destroy_later()

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
    def __add_to_history(self, widget):
        """
            Add widget to history or rebase history at widget position
        """
        if widget in self.__history:
            index = self.__history.index(widget)
            self.__history = self.__history[0:index + 1]
        else:
            self.__history.append(widget)

    def __on_child_destroy(self, widget):
        """
            Remove from history
            @param widget as Gtk.Widget
        """
        if widget in self.__history:
            self.__history.remove(widget)


class AdaptiveWindow:
    """
        Handle window resizing and window's children workflow
        This class needs a stack and n paned
    """
    _ADAPTIVE_STACK = 600

    gsignals = {
        "adaptive-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "show-can-go-back": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
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
        self.__paned = []

    def set_stack(self, stack):
        """
            Add stack to adaptive mode
            @param stack as AdaptiveStack
        """
        self.__stack = stack

    def add_paned(self, paned, child):
        """
            Add paned to adaptive mode
            @param paned as Gtk.Paned
            @param child as Gtk.Widget
        """
        self.__paned.append((paned, child))

    def go_back(self):
        """
            Go back in container stack
        """
        if self.__stack.history:
            visible = self.__stack.get_visible_child()
            for widget in reversed(self.__stack.history):
                if widget != visible and widget.get_visible():
                    self.__stack.set_visible_child(widget)
                    break
            if len(self.__stack.history) <= 1:
                self.emit("can-go-back-changed", False)

    def go_home(self):
        """
            Go back to first page
        """
        if self.__stack.history:
            visible = self.__stack.get_visible_child()
            widget = self.__stack.history[0]
            if widget != visible and widget.get_visible():
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
        return len(self.__stack.history) > 1

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
    def __set_adaptive_stack(self, b):
        """
            Move paned child to stack
            @param b as bool
        """
        self.__adaptive_timeout_id = None
        if b:
            self.__stack.set_transition_type(Gtk.StackTransitionType.NONE)
            self._adaptive_stack = True
            child = []
            can_go_back = self.__stack.get_visible_child() is not None
            self.__stack.reset_history()
            for (p, c) in self.__paned:
                child.append(p.get_child1())
                p.remove(c)
                self.__stack.add(c)
            self.emit("can-go-back-changed", can_go_back)
            self.emit("show-can-go-back", True)
            self.emit("adaptive-changed", True)
            self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        else:
            self.__stack.set_transition_type(Gtk.StackTransitionType.NONE)
            self._adaptive_stack = False
            # Move wanted child to paned
            for (p, c) in self.__paned:
                self.__stack.remove(c)
                p.add1(c)
            self.emit("show-can-go-back", False)
            self.emit("adaptive-changed", False)
            self.__stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

    def __on_configure_event(self, widget, event):
        """
            Delay event
            @param widget as Gtk.Window
            @param event as Gdk.EventConfigure
        """
        self.do_adaptive_mode(widget.get_size()[0])
