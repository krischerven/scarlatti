# Copyright (c) 2014-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from scarlatti.logger import Logger
from scarlatti.utils_file import decodeUnicode, splitUnicode
from scarlatti.tag_frame import FrameTag
from scarlatti.define import UTF_16_ENCODING, UTF_16BE_ENCODING


class FrameLangTag(FrameTag):
    """
        Bytes representing a text with lang frame
    """

    def __init__(self, bytes):
        """
            Init tag reader
            @param bytes as bytes
        """
        FrameTag.__init__(self, bytes)

    @property
    def string(self):
        """
            String representation of data
            @return str/None
        """
        try:
            (d, t) = splitUnicode(self.frame, self.encoding)
            if self.encoding in [UTF_16_ENCODING, UTF_16BE_ENCODING]:
                (start, end) = t.split(b"\x00\x00\xff", 1)
                end = b"\xff" + end
            else:
                (start, end) = t.split(b"\x00", 1)
            return decodeUnicode(end, self.encoding)
        except Exception as e:
            Logger.error("FrameLangTag::string: %s, %s", e, self.frame)
            return ""
