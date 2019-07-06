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

from gi.repository import Gtk, GLib

from gettext import gettext as _

from lollypop.define import App, MARGIN
from lollypop.utils import on_query_tooltip, on_realize
from lollypop.objects import Album
from lollypop.widgets_artist_banner import ArtistBannerWidget
from lollypop.logger import Logger


class ArtistViewCommon:
    """
        Widgets and methods share between ArtistView and ArtistViewSmall
    """

    def __init__(self):
        """
            Init view
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ArtistView.ui")
        builder.connect_signals(self)
        builder.get_object("box-button").set_margin_end(MARGIN)
        self._artwork = builder.get_object("artwork")
        self._title_label = builder.get_object("artist")
        self._title_label.connect("realize", on_realize)
        self._title_label.connect("query-tooltip", on_query_tooltip)
        self._title_label.set_property("has-tooltip", True)
        self._jump_button = builder.get_object("jump-button")
        self._add_button = builder.get_object("add-button")
        self._play_button = builder.get_object("play-button")
        self._buttons = builder.get_object("buttons")
        self._banner = ArtistBannerWidget(self._artist_ids[0])
        self._banner.add_overlay(self._buttons)
        self._banner.show()
        builder.get_object("box-button").set_margin_end(MARGIN)
        artists = []
        for artist_id in self._artist_ids:
            artists.append(App().artists.get_name(artist_id))
        self._title_label.set_markup(
            GLib.markup_escape_text(", ".join(artists)))

#######################
# PROTECTED           #
#######################
    def _update_icon(self, add):
        """
            Set icon for Artist +/-
            @param add as bool
        """
        if add:
            # Translators: artist context
            self._add_button.set_tooltip_text(_("Add to current playlist"))
            self._add_button.get_image().set_from_icon_name(
                "list-add-symbolic",
                Gtk.IconSize.DND)
        else:
            # Translators: artist context
            self._add_button.set_tooltip_text(
                _("Remove from current playlist"))
            self._add_button.get_image().set_from_icon_name(
                "list-remove-symbolic",
                Gtk.IconSize.DND)

    def _on_label_realize(self, eventbox):
        pass

    def _on_artwork_box_realize(self, eventbox):
        pass

    def _on_image_button_release(self, eventbox, event):
        pass

    def _on_jump_button_clicked(self, button):
        pass

    def _on_label_button_release(self, eventbox, event):
        """
            Show artists information
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
        """
        if len(self._artist_ids) == 1:
            from lollypop.pop_information import InformationPopover
            self.__pop_info = InformationPopover(True)
            self.__pop_info.set_relative_to(eventbox)
            self.__pop_info.populate(self._artist_ids[0])
            self.__pop_info.show()

    def _on_play_clicked(self, widget):
        """
            Play artist albums
        """
        try:
            if App().player.is_party:
                App().lookup_action("party").change_state(
                    GLib.Variant("b", False))
            App().player.play_albums_for_filter(None,
                                                self._genre_ids,
                                                self._artist_ids)
            self._update_icon(False)
        except Exception as e:
            Logger.error("ArtistView::_on_play_clicked: %s" % e)

    def _on_add_clicked(self, widget):
        """
            Add artist albums
        """
        try:
            if App().settings.get_value("show-performers"):
                album_ids = App().tracks.get_album_ids(self._artist_ids,
                                                       self._genre_ids)
            else:
                album_ids = App().albums.get_ids(self._artist_ids,
                                                 self._genre_ids)
            icon_name = self._add_button.get_image().get_icon_name()[0]
            add = icon_name == "list-add-symbolic"
            for album_id in album_ids:
                if add and album_id not in App().player.album_ids:
                    App().player.add_album(Album(album_id,
                                                 self._genre_ids,
                                                 self._artist_ids))
                elif not add and album_id in App().player.album_ids:
                    App().player.remove_album_by_id(album_id)
            if len(App().player.album_ids) == 0:
                App().player.stop()
            elif App().player.current_track.album.id\
                    not in App().player.album_ids:
                App().player.skip_album()
            self._update_icon(not add)
        except Exception as e:
            Logger.error("ArtistView::_on_add_clicked: %s" % e)

    def _on_similars_button_toggled(self, button):
        """
            Show similar artists
            @param button as Gtk.Button
        """
        if button.get_active():
            from lollypop.pop_similars import SimilarsPopover
            popover = SimilarsPopover()
            popover.set_relative_to(button)
            popover.populate(self._artist_ids)
            popover.connect("closed", lambda x: button.set_active(False))
            popover.popup()

#######################
# PRIVATE             #
#######################
