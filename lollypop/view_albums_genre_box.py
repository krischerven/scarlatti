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

from lollypop.view_flowbox import FlowBoxView
from lollypop.widgets_albums_genre import AlbumsGenreWidget
from lollypop.define import App, Type, ViewType
from lollypop.utils import get_icon_name


class AlbumsGenreBoxView(FlowBoxView):
    """
        Show decades in a FlowBox
    """

    def __init__(self, view_type):
        """
            Init decade view
            @param view_type as ViewType
        """
        FlowBoxView.__init__(self, view_type)
        self._widget_class = AlbumsGenreWidget
        self._empty_icon_name = get_icon_name(Type.GENRES)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            return App().genres.get_ids()

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, {}, int, int)
        """
        if self._view_type & ViewType.SCROLLED:
            position = self._scrolled.get_vadjustment().get_value()
        else:
            position = 0
        return ({"view_type": self._view_type}, self._sidebar_id, position)

#######################
# PROTECTED           #
#######################
    def _add_items(self, item_ids, *args):
        """
            Add albums to the view
            Start lazy loading
            @param item ids as [int]
        """
        widget = FlowBoxView._add_items(self, item_ids, self._view_type)
        if widget is not None:
            widget.connect("overlayed", self.on_overlayed)

    def _on_item_activated(self, flowbox, widget):
        """
            Show Context view for activated album
            @param flowbox as Gtk.Flowbox
            @param widget as PlaylistRoundedWidget
        """
        if not self._view_type & ViewType.SMALL and\
                FlowBoxView._on_item_activated(self, flowbox, widget):
            return
        App().window.container.show_view([Type.GENRES], widget.data)
