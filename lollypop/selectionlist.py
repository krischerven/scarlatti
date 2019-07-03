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

from gi.repository import Gtk, Gdk, GLib, GObject, Pango

from gettext import gettext as _
from locale import strcoll

from lollypop.view import LazyLoadingView
from lollypop.fastscroll import FastScroll
from lollypop.define import Type, App, ArtSize, SelectionListMask
from lollypop.define import SidebarContent, ArtBehaviour, ViewType
from lollypop.logger import Logger
from lollypop.utils import get_icon_name, on_query_tooltip
from lollypop.shown import ShownLists, ShownPlaylists


class TypeAheadPopover(Gtk.Popover):
    """
        Special popover for find as type
    """

    def __init__(self):
        """
            Init popover
        """
        Gtk.Popover.__init__(self)
        self.__entry = Gtk.Entry()
        self.__entry.show()
        self.add(self.__entry)
        self.get_style_context().add_class("padding")
        self.connect("unmap", self.__on_unmap)

    @property
    def entry(self):
        """
            Get popover entry
            @return Gtk.Entry
        """
        return self.__entry

#######################
# PRIVATE             #
#######################
    def __on_unmap(self, popover):
        """
            Clear entry
            @param popover as Gtk.popover
        """
        self.__entry.set_text("")


class SelectionListRow(Gtk.ListBoxRow):
    """
        A selection list row
    """

    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def get_best_height(widget):
        """
            Calculate widget height
            @param widget as Gtk.Widget
        """
        ctx = widget.get_pango_context()
        layout = Pango.Layout.new(ctx)
        layout.set_text("a", 1)
        font_height = int(layout.get_pixel_size()[1])
        return font_height

    def __init__(self, rowid, name, sortname, mask, height):
        """
            Init row
            @param rowid as int
            @param name as str
            @param sortname as str
            @param mask as SelectionListMask
            @param height as str
        """
        Gtk.ListBoxRow.__init__(self)
        self.__rowid = rowid
        self.__name = name
        self.__sortname = sortname
        self.__mask = mask

        if rowid == Type.SEPARATOR:
            height = -1
            self.set_sensitive(False)
        elif self.__mask & SelectionListMask.ARTISTS and\
                self.__rowid >= 0 and\
                App().settings.get_value("artist-artwork"):
            self.get_style_context().add_class("row")
            if height < ArtSize.ARTIST_SMALL:
                height = ArtSize.ARTIST_SMALL
            # Padding => application.css
            height += 12
        elif App().settings.get_enum("sidebar-content") ==\
                SidebarContent.DEFAULT:
            self.get_style_context().add_class("row-big")
            # Padding => application.css
            height += 30
        else:
            self.get_style_context().add_class("row")
        self.set_size_request(-1, height)

    def populate(self):
        """
            Populate widget
        """
        if self.__rowid == Type.SEPARATOR:
            separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
            separator.show()
            self.add(separator)
            self.set_sensitive(False)
            self.emit("populated")
        else:
            self.__grid = Gtk.Grid()
            self.__grid.set_column_spacing(7)
            self.__artwork = Gtk.Image.new()
            self.__label = Gtk.Label.new()
            self.__label.set_markup(GLib.markup_escape_text(self.__name))
            self.__label.set_ellipsize(Pango.EllipsizeMode.END)
            self.__label.set_property("has-tooltip", True)
            self.__label.connect("query-tooltip", on_query_tooltip)
            self.__label.show()
            self.__grid.show()
            self.__grid.show()
            self.__grid.add(self.__artwork)
            self.__grid.add(self.__label)
            if self.__mask & SelectionListMask.ARTISTS:
                self.__grid.set_margin_end(20)
            self.add(self.__grid)
            self.set_artwork()

    def set_label(self, string):
        """
            Set label for row
            @param string as str
        """
        self.__name = string
        self.__label.set_markup(GLib.markup_escape_text(string))

    def set_artwork(self):
        """
            set_artwork widget
        """
        if self.__rowid == Type.SEPARATOR:
            pass
        elif self.__mask & SelectionListMask.ARTISTS and\
                self.__rowid >= 0 and\
                App().settings.get_value("artist-artwork"):
            App().art_helper.set_artist_artwork(
                                    self.__name,
                                    ArtSize.ARTIST_SMALL,
                                    ArtSize.ARTIST_SMALL,
                                    self.get_scale_factor(),
                                    ArtBehaviour.ROUNDED |
                                    ArtBehaviour.CROP_SQUARE |
                                    ArtBehaviour.CACHE,
                                    self.__on_artist_artwork)
            self.__artwork.show()
        elif self.__rowid < 0:
            icon_name = get_icon_name(self.__rowid, self.__mask)
            self.__artwork.set_from_icon_name(icon_name,
                                              Gtk.IconSize.BUTTON)
            self.__artwork.show()
            self.emit("populated")
        else:
            self.__artwork.hide()
            self.emit("populated")

    @property
    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return True

    @property
    def name(self):
        """
            Get row name
            @return str
        """
        return self.__name

    @property
    def sortname(self):
        """
            Get row sortname
            @return str
        """
        return self.__sortname

    @property
    def id(self):
        """
            Get row id
            @return int
        """
        return self.__rowid

#######################
# PRIVATE             #
#######################
    def __on_artist_artwork(self, surface):
        """
            Set artist artwork
            @param surface as cairo.Surface
        """
        if surface is None:
            self.__artwork.get_style_context().add_class("artwork-icon")
            self.__artwork.set_size_request(ArtSize.ARTIST_SMALL,
                                            ArtSize.ARTIST_SMALL)
            self.__artwork.set_from_icon_name(
                                              "avatar-default-symbolic",
                                              Gtk.IconSize.DND)
        else:
            self.__artwork.get_style_context().remove_class("artwork-icon")
            self.__artwork.set_from_surface(surface)
        self.emit("populated")


class SelectionList(LazyLoadingView):
    """
        A list for artists/genres
    """
    __gsignals__ = {
        "populated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "pass-focus": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, base_type):
        """
            Init Selection list ui
            @param base_type as SelectionListMask
        """
        LazyLoadingView.__init__(self, ViewType.NOT_ADAPTIVE)
        self.__base_type = base_type
        self.__sort = False
        self.__mask = 0
        self.__height = SelectionListRow.get_best_height(self)
        self._listbox = Gtk.ListBox()
        self._listbox.connect("button-release-event",
                              self.__on_button_release_event)
        self._listbox.connect("key-press-event",
                              self.__on_key_press_event)
        self._listbox.set_sort_func(self.__sort_func)
        self._listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self._listbox.set_filter_func(self._filter_func)
        self._listbox.show()
        self._viewport.add(self._listbox)
        overlay = Gtk.Overlay.new()
        overlay.set_hexpand(True)
        overlay.set_vexpand(True)
        overlay.show()
        overlay.add(self._scrolled)
        self.__fastscroll = FastScroll(self._listbox,
                                       self._scrolled)
        overlay.add_overlay(self.__fastscroll)
        self.add(overlay)
        self.get_style_context().add_class("sidebar")
        App().art.connect("artist-artwork-changed",
                          self.__on_artist_artwork_changed)
        self.__type_ahead_popover = TypeAheadPopover()
        self.__type_ahead_popover.set_relative_to(self._scrolled)
        self.__type_ahead_popover.entry.connect("activate",
                                                self.__on_type_ahead_activate)
        self.__type_ahead_popover.entry.connect("changed",
                                                self.__on_type_ahead_changed)

    def mark_as(self, type):
        """
            Mark list as artists list
            @param type as SelectionListMask
        """
        self.__mask = self.__base_type | type

    def populate(self, values):
        """
            Populate view with values
            @param [(int, str, optional str)], will be deleted
        """
        self.__sort = False
        self._scrolled.get_vadjustment().set_value(0)
        self.clear()
        self.__add_values(values)

    def remove_value(self, object_id):
        """
            Remove id from list
            @param object_id as int
        """
        for child in self._listbox.get_children():
            if child.id == object_id:
                child.destroy()
                break

    def add_value(self, value):
        """
            Add item to list
            @param value as (int, str, optional str)
        """
        self.__sort = True
        # Do not add value if already exists
        for child in self._listbox.get_children():
            if child.id == value[0]:
                return
        row = self.__add_value(value[0], value[1], value[2])
        row.populate()

    def update_value(self, object_id, name):
        """
            Update object with new name
            @param object_id as int
            @param name as str
        """
        found = False
        for child in self._listbox.get_children():
            if child.id == object_id:
                child.set_label(name)
                found = True
                break
        if not found:
            self.__fastscroll.clear()
            row = self.__add_value(object_id, name, name)
            row.populate()
            if self.__mask & SelectionListMask.ARTISTS:
                self.__fastscroll.populate()

    def update_values(self, values):
        """
            Update view with values
            @param [(int, str, optional str)]
        """
        if self.__mask & SelectionListMask.ARTISTS:
            self.__fastscroll.clear()
        # Remove not found items
        value_ids = set([v[0] for v in values])
        for child in self._listbox.get_children():
            if child.id not in value_ids:
                self.remove_value(child.id)
        # Add items which are not already in the list
        item_ids = set([child.id for child in self._listbox.get_children()])
        for value in values:
            if not value[0] in item_ids:
                row = self.__add_value(value[0], value[1], value[2])
                row.populate()
        if self.__mask & SelectionListMask.ARTISTS:
            self.__fastscroll.populate()

    def select_ids(self, ids=[]):
        """
            Select listbox items
            @param ids as [int]
        """
        self._listbox.unselect_all()
        for row in self._listbox.get_children():
            if row.id in ids:
                self._listbox.select_row(row)
        for row in self._listbox.get_selected_rows():
            row.activate()
            break

    def grab_focus(self):
        """
            Grab focus on treeview
        """
        self._listbox.grab_focus()

    def clear(self):
        """
            Clear treeview
        """
        for child in self._listbox.get_children():
            child.destroy()
        self.__fastscroll.clear()
        self.__fastscroll.clear_chars()

    def get_headers(self, mask):
        """
            Return headers
            @param mask as SelectionListMask
            @return items as [(int, str)]
        """
        lists = ShownLists.get(mask)
        if mask & SelectionListMask.LIST_ONE and App().window.is_adaptive:
            lists += [(Type.SEARCH, _("Search"), _("Search"))]
            lists += [
                (Type.CURRENT, _("Current playlist"), _("Current playlist"))]
        if lists and\
                App().settings.get_enum("sidebar-content") !=\
                SidebarContent.DEFAULT:
            lists.append((Type.SEPARATOR, "", ""))
        return lists

    def get_playlist_headers(self):
        """
            Return playlist headers
            @return items as [(int, str)]
        """
        lists = ShownPlaylists.get()
        if lists and\
                App().settings.get_enum("sidebar-content") !=\
                SidebarContent.DEFAULT:
            lists.append((Type.SEPARATOR, "", ""))
        return lists

    def select_first(self):
        """
            Select first available item
        """
        try:
            self._listbox.unselect_all()
            row = self._listbox.get_children()[0]
            row.activate()
        except Exception as e:
            Logger.warning("SelectionList::select_first(): %s", e)

    def redraw(self):
        """
            Redraw list
        """
        for row in self._listbox.get_children():
            row.set_artwork()

    @property
    def type_ahead_popover(self):
        """
            Type ahead popover
            @return TypeAheadPopover
        """
        return self.__type_ahead_popover

    @property
    def listbox(self):
        """
            Get listbox
            @return Gtk.ListBox
        """
        return self._listbox

    @property
    def should_destroy(self):
        """
            True if view should be destroyed
            @return bool
        """
        return False

    @property
    def mask(self):
        """
            Get selection list type
            @return bit mask
        """
        return self.__mask

    @property
    def count(self):
        """
            Get items count in list
            @return int
        """
        return len(self._listbox.get_children())

    @property
    def selected_ids(self):
        """
            Get selected ids
            @return array of ids as [int]
        """
        return [row.id for row in self._listbox.get_selected_rows()]

#######################
# PRIVATE             #
#######################
    def __scroll_to_row(self, row):
        """
            Scroll to row
            @param row as SelectionListRow
        """
        coordinates = row.translate_coordinates(self._listbox, 0, 0)
        if coordinates:
            self._scrolled.get_vadjustment().set_value(coordinates[1])

    def __add_values(self, values):
        """
            Add values to the list
            @param items as [(int, str, str)]
        """
        if values:
            (rowid, name, sortname) = values.pop(0)
            row = self.__add_value(rowid, name, sortname)
            self._lazy_queue.append(row)
            GLib.idle_add(self.__add_values, values)
        else:
            if self.__mask & SelectionListMask.ARTISTS:
                self.__fastscroll.populate()
            self.__sort = True
            self.emit("populated")
            self.lazy_loading()
            # Scroll to first selected item
            for row in self._listbox.get_selected_rows():
                GLib.idle_add(self.__scroll_to_row, row)
                break

    def __add_value(self, rowid, name, sortname):
        """
            Add value to list
            @param rowid as int
            @param name as str
            @param sortname as str
            @return row as SelectionListRow
        """
        if rowid > 0 and sortname and name and\
                self.__mask & SelectionListMask.ARTISTS:
            self.__fastscroll.add_char(sortname[0])
        row = SelectionListRow(rowid, name, sortname,
                               self.__mask, self.__height)
        row.show()
        self._listbox.add(row)
        return row

    def __sort_func(self, row_a, row_b):
        """
            Sort rows
            @param row_a as SelectionListRow
            @param row_b as SelectionListRow
        """
        if not self.__sort:
            return False
        a_index = row_a.id
        b_index = row_b.id

        # Static vs static
        if a_index < 0 and b_index < 0:
            return a_index < b_index
        # Static entries always on top
        elif b_index < 0:
            return True
        # Static entries always on top
        if a_index < 0:
            return False
        # String comparaison for non static
        else:
            if self.__mask & SelectionListMask.ARTISTS:
                a = row_a.sortname
                b = row_b.sortname
            else:
                a = row_a.name
                b = row_b.name
            return strcoll(a, b)

    def __on_key_press_event(self, listbox, event):
        """
            Pass focus as signal
            @param listbox as Gtk.ListBox
            @param event as Gdk.Event
        """
        if event.keyval in [Gdk.KEY_Left, Gdk.KEY_Right]:
            self.emit("pass-focus")

    def __on_button_release_event(self, listbox, event):
        """
            Handle modifier
            @param listbox as Gtk.ListBox
            @param event as Gdk.Event
        """
        if event.button != 1 and\
                self.__base_type in [SelectionListMask.LIST_ONE,
                                     SelectionListMask.LIST_TWO]:
            from lollypop.menu_selectionlist import SelectionListMenu
            from lollypop.widgets_utils import Popover
            row = listbox.get_row_at_y(event.y)
            if row is not None:
                menu = SelectionListMenu(self, row.id, self.mask)
                popover = Popover()
                popover.bind_model(menu, None)
                popover.set_relative_to(listbox)
                rect = Gdk.Rectangle()
                rect.x = event.x
                rect.y = event.y
                rect.width = rect.height = 1
                popover.set_pointing_to(rect)
                popover.popup()
                return True
        elif event.button == 1:
            state = event.get_state()
            static_selected = self.selected_ids and self.selected_ids[0] < 0
            if (not state & Gdk.ModifierType.CONTROL_MASK and
                    not state & Gdk.ModifierType.SHIFT_MASK) or\
                    static_selected:
                listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            row = listbox.get_row_at_y(event.y)
            if row is not None and not (row.id < 0 and self.selected_ids):
                # User clicked on random, clear cached one
                if row.id == Type.RANDOMS:
                    App().albums.clear_cached_randoms()
                    App().tracks.clear_cached_randoms()
            listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

    def __on_artist_artwork_changed(self, art, artist):
        """
            Update row
            @param art as Art
            @param artist as str
        """
        if self.__mask & SelectionListMask.ARTISTS:
            for row in self._listbox.get_children():
                if row.id >= 0 and row.name == artist:
                    row.set_artwork()
                    break

    def __on_type_ahead_activate(self, entry):
        """
            Close popover and activate row
            @param entry as Gtk.Entry
        """
        self._listbox.unselect_all()
        self.__type_ahead_popover.popdown()
        for row in self._listbox.get_children():
            style_context = row.get_style_context()
            if style_context.has_class("typeahead"):
                row.activate()
            style_context.remove_class("typeahead")

    def __on_type_ahead_changed(self, entry):
        """
            Search row and scroll down
            @param entry as Gtk.Entry
        """
        search = entry.get_text().lower()
        for row in self._listbox.get_children():
            style_context = row.get_style_context()
            style_context.remove_class("typeahead")
        if not search:
            return
        for row in self._listbox.get_children():
            if row.name.lower().find(search) != -1:
                style_context = row.get_style_context()
                style_context.add_class("typeahead")
                GLib.idle_add(self.__scroll_to_row, row)
                break
