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

from struct import unpack
from warnings import warn

# Flags in the STRING Section
SORTED_FLAG = 1 << 0
UTF8_FLAG = 1 << 8


class StringBlock(object):
    """
    StringBlock is a CHUNK inside an AXML File
    It contains all strings, which are used by referecing to ID's
    TODO might migrate this block into the ARSCParser, as it it not a "special" block but a normal tag.
    """
    def __init__(self, buff, header):
        self._cache = {}
        self.header = header
        # We already read the header (which was chunk_type and chunk_size
        # Now, we read the string_count:
        self.stringCount = unpack('<i', buff.read(4))[0]
        # style_count
        self.styleOffsetCount = unpack('<i', buff.read(4))[0]

        # flags
        self.flags = unpack('<i', buff.read(4))[0]
        self.m_isUTF8 = ((self.flags & UTF8_FLAG) != 0)

        # string_pool_offset
        # The string offset is counted from the beginning of the string section
        self.stringsOffset = unpack('<i', buff.read(4))[0]
        # style_pool_offset
        # The styles offset is counted as well from the beginning of the string section
        self.stylesOffset = unpack('<i', buff.read(4))[0]

        # Check if they supplied a stylesOffset even if the count is 0:
        if self.styleOffsetCount == 0 and self.stylesOffset > 0:
            warn("Styles Offset given, but styleCount is zero.")

        self.m_stringOffsets = []
        self.m_styleOffsets = []
        self.m_charbuff = ""
        self.m_styles = []

        # Next, there is a list of string following
        # This is only a list of offsets (4 byte each)
        for i in range(0, self.stringCount):
            self.m_stringOffsets.append(unpack('<i', buff.read(4))[0])

        # And a list of styles
        # again, a list of offsets
        for i in range(0, self.styleOffsetCount):
            self.m_styleOffsets.append(unpack('<i', buff.read(4))[0])

        # FIXME it is probably better to parse n strings and not the size
        size = self.header.size - self.stringsOffset

        # if there are styles as well, we do not want to read them too.
        # Only read them, if no
        if self.stylesOffset != 0 and self.styleOffsetCount != 0:
            size = self.stylesOffset - self.stringsOffset

        # FIXME unaligned
        if (size % 4) != 0:
            warn("Size of strings is not aligned by four bytes.")

        self.m_charbuff = buff.read(size)

        if self.stylesOffset != 0 and self.styleOffsetCount != 0:
            size = self.header.size - self.stylesOffset

            # FIXME unaligned
            if (size % 4) != 0:
                warn("Size of styles is not aligned by four bytes.")

            for i in range(0, size // 4):
                self.m_styles.append(unpack('<i', buff.read(4))[0])

    def getString(self, idx):
        if idx in self._cache:
            return self._cache[idx]

        if idx < 0 or not self.m_stringOffsets or idx >= len(
                self.m_stringOffsets):
            return ""

        offset = self.m_stringOffsets[idx]

        if self.m_isUTF8:
            self._cache[idx] = self.decode8(offset)
        else:
            self._cache[idx] = self.decode16(offset)

        return self._cache[idx]

    def getStyle(self, idx):
        # FIXME
        return self.m_styles[idx]

    def decode8(self, offset):
        str_len, skip = self.decodeLength(offset, 1)
        offset += skip

        encoded_bytes, skip = self.decodeLength(offset, 1)
        offset += skip

        data = self.m_charbuff[offset: offset + encoded_bytes]

        return self.decode_bytes(data, 'utf-8', str_len)

    def decode16(self, offset):
        str_len, skip = self.decodeLength(offset, 2)
        offset += skip

        encoded_bytes = str_len * 2

        data = self.m_charbuff[offset: offset + encoded_bytes]

        return self.decode_bytes(data, 'utf-16', str_len)

    def decode_bytes(self, data, encoding, str_len):
        string = data.decode(encoding, 'replace')
        if len(string) != str_len:
            warn("invalid decoded string length")
        return string

    def decodeLength(self, offset, sizeof_char):
        length = self.m_charbuff[offset]

        sizeof_2chars = sizeof_char << 1
        fmt_chr = 'B' if sizeof_char == 1 else 'H'
        fmt = "<2" + fmt_chr

        length1, length2 = unpack(
            fmt, self.m_charbuff[offset:(offset + sizeof_2chars)])

        highbit = 0x80 << (8 * (sizeof_char - 1))

        if (length & highbit) != 0:
            return (
                (length1 & ~highbit) << (8 * sizeof_char)
            ) | length2, sizeof_2chars
        else:
            return length1, sizeof_char

    def show(self):
        print("StringBlock(%x, %x, %x, %x, %x, %x" % (
            self.start,
            self.header,
            self.header_size,
            self.chunkSize,
            self.stringsOffset,
            self.flags))
        for i in range(0, len(self.m_stringOffsets)):
            print(i, repr(self.getString(i)))
