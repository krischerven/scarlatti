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
from lollypop.widgets_albums_decade import AlbumsDecadeWidget
from lollypop.define import App, Type, ViewType
from lollypop.utils import get_icon_name


class DecadesBoxView(FlowBoxView):
    """
        Show decades in a FlowBox
    """

    def __init__(self):
        """
            Init decade view
        """
        FlowBoxView.__init__(self, ViewType.SCROLLED)
        self._widget_class = AlbumsDecadeWidget
        self._empty_icon_name = get_icon_name(Type.YEARS)
        self.add_widget(self._box)

    def populate(self):
        """
            Populate view
        """
        def on_load(items):
            FlowBoxView.populate(self, items)

        def load():
            (years, unknown) = App().albums.get_years()
            decades = []
            decade = []
            current_d = None
            for year in sorted(years):
                d = year // 10
                if current_d is not None and current_d != d:
                    current_d = d
                    decades.append(decade)
                    decade = []
                current_d = d
                decade.append(year)
            if decade:
                decades.append(decade)
            return decades

        App().task_helper.run(load, callback=(on_load,))

    @property
    def args(self):
        """
            Get default args for __class__, populate() plus sidebar_id and
            scrolled position
            @return ({}, int, int)
        """
        return ({"view_type": self.view_type}, self.sidebar_id, self.position)

#######################
# PROTECTED           #
#######################
    def _add_items(self, item_ids, *args):
        """
            Add albums to the view
            Start lazy loading
            @param item ids as [int]
        """
        FlowBoxView._add_items(self, item_ids, self._view_type)

    def _on_child_activated(self, flowbox, child):
        """
            Enter child
            @param flowbox as Gtk.FlowBox
            @param child as Gtk.FlowBoxChild
        """
        App().window.container.show_view([Type.YEARS], child.data)
