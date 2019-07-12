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

from gi.repository import Gtk, Gdk, GLib

from lollypop.define import App, MARGIN_SMALL


class TypeAheadWidget(Gtk.Revealer):
    """
        Type ahead widget
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Revealer.__init__(self)
        self.__list_two_map_signal_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/TypeAhead.ui")
        builder.connect_signals(self)
        widget = builder.get_object("widget")
        widget.set_margin_top(MARGIN_SMALL)
        widget.set_margin_bottom(2)
        self.__entry = builder.get_object("entry")
        self.__next_button = builder.get_object("next_button")
        self.__prev_button = builder.get_object("prev_button")
        self.__next_button.connect("clicked", lambda x: self.__search_next())
        self.__prev_button.connect("clicked", lambda x: self.__search_prev())
        self.add(widget)

    def update_indicators(self, show):
        """
            Update list/views indicator
            @param show as bool
        """
        indicators = self.__get_indicators(True)
        for indicator in indicators:
            if show:
                indicator.show()
            else:
                indicator.hide()

    def set_active_indicator(self, view):
        """
            Mark view indicator as active
            @param widget as View
        """
        for _view in [App().window.container.list_one,
                      App().window.container.list_two,
                      App().window.container.view]:
            if _view is None:
                continue
            if view == _view:
                _view.indicator.set_state_flags(Gtk.StateFlags.SELECTED, True)
            else:
                _view.indicator.set_state_flags(Gtk.StateFlags.NORMAL, True)

    @property
    def entry(self):
        """
            Get popover entry
            @return Gtk.Entry
        """
        return self.__entry

#######################
# PROTECTED           #
#######################
    def _on_type_ahead_changed(self, entry):
        """
            Filter current widget
            @param entry as Gtk.entry
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.search_for_child(entry.get_text().lower())

    def _on_type_ahead_activate(self, entry):
        """
            Activate row
            @param entry as Gtk.Entry
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.activate_child()
            GLib.idle_add(self.__activate_next_view)
            self.__entry.set_text("")
            self.__entry.grab_focus()

    def _on_entry_key_press_event(self, entry, event):
        """
            Handle special keys
            @param entry as Gtk.Entry
            @param Event as Gdk.EventKey
        """
        if (event.state & Gdk.ModifierType.SHIFT_MASK and
                event.state & Gdk.ModifierType.CONTROL_MASK) or\
                event.keyval == Gdk.KEY_Up or\
                event.keyval == Gdk.KEY_Down:
            return True

    def _on_entry_key_release_event(self, entry, event):
        """
            Handle special keys
            @param entry as Gtk.Entry
            @param Event as Gdk.EventKey
        """
        if event.state & (Gdk.ModifierType.SHIFT_MASK |
                          Gdk.ModifierType.CONTROL_MASK):
            if event.keyval == Gdk.KEY_Right:
                self.__activate_next_view()
            elif event.keyval == Gdk.KEY_Left:
                self.__activate_prev_view()
        elif event.keyval == Gdk.KEY_Up:
            self.__search_prev()
        elif event.keyval == Gdk.KEY_Down:
            self.__search_next()

#######################
# PRIVATE             #
#######################
    def __search_prev(self):
        """
            Search previous item
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.search_prev(self.__entry.get_text().lower())

    def __search_next(self):
        """
            Search next item
        """
        widget = self.__get_widget()
        if widget is not None:
            widget.search_next(self.__entry.get_text().lower())

    def __get_widget(self):
        """
            Get widget for activated button
            @return Gtk.Widget
        """
        if App().window.container.list_one.indicator.get_state_flags() &\
                Gtk.StateFlags.SELECTED:
            return App().window.container.list_one
        elif App().window.container.list_two.indicator.get_state_flags() &\
                Gtk.StateFlags.SELECTED:
            return App().window.container.list_two
        else:
            return App().window.container.stack

    def __get_indicators(self, show_hidden=False):
        """
            Get indicator
            @param show_hidden as bool
            @return Gtk.Widget
        """
        indicators = []
        for view in [App().window.container.list_one,
                     App().window.container.list_two,
                     App().window.container.view]:
            if view is not None and\
                    (view.get_visible() or show_hidden) and\
                    hasattr(view, "indicator"):
                indicators.append(view.indicator)
        return indicators

    def __activate_next_view(self):
        """
            Activate next view
        """
        active = None
        indicators = self.__get_indicators()
        for indicator in indicators:
            if indicator.get_state_flags() &\
                    Gtk.StateFlags.SELECTED:
                active = indicator
                break
        index = indicators.index(active)
        if index + 1 < len(indicators):
            indicators[index + 1].set_state_flags(Gtk.StateFlags.SELECTED,
                                                  True)
            active.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def __activate_prev_view(self):
        """
            Activate prev view
        """
        active = None
        indicators = self.__get_indicators()
        for indicator in indicators:
            if indicator.get_state_flags() &\
                    Gtk.StateFlags.SELECTED:
                active = indicator
                break
        index = indicators.index(active)
        if index > 0:
            indicators[index - 1].set_state_flags(Gtk.StateFlags.SELECTED,
                                                  True)
            active.set_state_flags(Gtk.StateFlags.NORMAL, True)
