# This file is part of Androguard.
#
# Copyright (C) 2012, Anthony Desnos <desnos at t0t0.fr>
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from warnings import warn
from struct import pack, unpack
from pyaxmlparser.utils import _range

UTF8_FLAG = 0x00000100
CHUNK_STRINGPOOL_TYPE = 0x001C0001
CHUNK_NULL_TYPE = 0x00000000


class StringBlock(object):

    def __init__(self, buff):
        self.start = buff.get_idx()
        self._cache = {}
        self.header_size, self.header = self.skipNullPadding(buff)

        self.chunkSize = unpack('<i', buff.read(4))[0]
        self.stringCount = unpack('<i', buff.read(4))[0]
        self.styleOffsetCount = unpack('<i', buff.read(4))[0]

        self.flags = unpack('<i', buff.read(4))[0]
        self.m_isUTF8 = ((self.flags & UTF8_FLAG) != 0)

        self.stringsOffset = unpack('<i', buff.read(4))[0]
        self.stylesOffset = unpack('<i', buff.read(4))[0]

        self.m_stringOffsets = []
        self.m_styleOffsets = []
        self.m_strings = []
        self.m_styles = []

        for i in _range(0, self.stringCount):
            self.m_stringOffsets.append(unpack('<i', buff.read(4))[0])

        for i in _range(0, self.styleOffsetCount):
            self.m_styleOffsets.append(unpack('<i', buff.read(4))[0])

        size = self.chunkSize - self.stringsOffset
        if self.stylesOffset != 0:
            size = self.stylesOffset - self.stringsOffset

        # FIXME
        if (size % 4) != 0:
            warn("ooo")

        for i in _range(0, size):
            self.m_strings.append(unpack('=b', buff.read(1))[0])

        if self.stylesOffset != 0:
            size = self.chunkSize - self.stylesOffset

            # FIXME
            if (size % 4) != 0:
                warn("ooo")

            for i in _range(0, int(size / 4)):
                self.m_styles.append(unpack('<i', buff.read(4))[0])

    def skipNullPadding(self, buff):
        def readNext(buff, first_run=True):
            header = unpack('<i', buff.read(4))[0]

            if header == CHUNK_NULL_TYPE and first_run:
                header = readNext(buff, first_run=False)
            elif header != CHUNK_STRINGPOOL_TYPE:
                warn("Invalid StringBlock header")

            return header

        header = readNext(buff)
        return header >> 8, header & 0xFF

    def getString(self, idx):
        if idx in self._cache:
            return self._cache[idx].replace("\x00", "")

        if idx < 0 or not self.m_stringOffsets or \
                idx >= len(self.m_stringOffsets):
            return ""

        offset = self.m_stringOffsets[idx]

        if not self.m_isUTF8:
            length = self.getShort2(self.m_strings, offset)
            offset += 2
            self._cache[idx] = self.decode(self.m_strings, offset, length)
        else:
            offset += self.getVarint(self.m_strings, offset)[1]
            varint = self.getVarint(self.m_strings, offset)

            offset += varint[1]
            length = varint[0]

            self._cache[idx] = self.decode2(self.m_strings, offset, length)

        return self._cache[idx].replace("\x00", "")

    def getStyle(self, idx):
        return
        print(idx)
        print(idx in self.m_styleOffsets, self.m_styleOffsets[idx])

        print(self.m_styles[0])

    def decode(self, array, offset, length):
        length = length * 2
        length = length + length % 2

        data = ""

        for i in _range(0, length):
            t_data = pack("=b", self.m_strings[offset + i])
            data += str(t_data, errors='ignore')
            if data[-2:] == "\x00\x00":
                break

        end_zero = data.find("\x00\x00")
        if end_zero != -1:
            data = data[:end_zero]

        return data

    def decode2(self, array, offset, length):
        data = ""

        for i in _range(0, length):
            t_data = pack("=b", self.m_strings[offset + i])
            data += str(t_data, errors='ignore')

        return data

    def getVarint(self, array, offset):
        val = array[offset]
        more = (val & 0x80) != 0
        val &= 0x7f

        if not more:
            return val, 1
        return val << 8 | array[offset + 1] & 0xff, 2

    def getShort(self, array, offset):
        value = array[offset / 4]
        if ((offset % 4) / 2) == 0:
            return value & 0xFFFF
        else:
            return value >> 16

    def getShort2(self, array, offset):
        return (array[offset + 1] & 0xff) << 8 | array[offset] & 0xff

    def show(self):
        return
        print(
            "StringBlock", hex(self.start), hex(self.header),
            hex(self.header_size), hex(self.chunkSize), hex(self.stringsOffset),
            self.m_stringOffsets)
        for i in _range(0, len(self.m_stringOffsets)):
            print(i, repr(self.getString(i)))
