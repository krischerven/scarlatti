from lollypop.define import App, Repeat
from lollypop.objects_album import Album


class AutoRandomPlayer:
    """
        Manage playback for AUTO_RANDOM when going to the end
    """

    def __init__(self):
        """
            Init player
        """
        self.connect("next-changed", self.__on_next_changed)

    def next_album(self):
        """
            Get next album to add.
        """
        for album_id in App().albums.get_randoms(limit=2):
            if album_id != self.current_track.album.id:
                return Album(album_id)
        return None

#######################
# PRIVATE             #
#######################
    def __on_next_changed(self, player):
        """
            Add a new album if playback finished and wanted by user
        """
        if App().settings.get_enum("repeat") != Repeat.AUTO_RANDOM or\
                player.next_track.id is not None:
            return
        album = self.next_album()
        if album:
            self.add_album(album)
