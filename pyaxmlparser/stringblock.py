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

from __future__ import unicode_literals
import logging
from struct import unpack

from pyaxmlparser.utils import is_python_3

# Flags in the STRING Section
SORTED_FLAG = 1 << 0
UTF8_FLAG = 1 << 8


class StringBlock(object):
    """
    StringBlock is a CHUNK inside an AXML File
    It contains all strings, which are used by referecing to ID's
    TODO might migrate this block into the ARSCParser, as it it not a 'special' block but a normal tag.
    """
    def __init__(self, buff, header, debug=False):
        self.log = logging.getLogger('pyaxmlparser.stringblock')
        self.log.setLevel(logging.DEBUG if debug else logging.CRITICAL)
        self._cache = {}
        self.header = header
        # We already read the header (which was chunk_type and chunk_size
        # Now, we read the string_count:
        self.string_count = unpack('<i', buff.read(4))[0]
        # style_count
        self.style_offset_count = unpack('<i', buff.read(4))[0]

        # flags
        self.flags = unpack('<i', buff.read(4))[0]
        self.is_utf8 = ((self.flags & UTF8_FLAG) != 0)

        # string_pool_offset
        # The string offset is counted from the beginning of the string section
        self.strings_offset = unpack('<i', buff.read(4))[0]
        # style_pool_offset
        # The styles offset is counted as well from the beginning of the string section
        self.styles_offset = unpack('<i', buff.read(4))[0]

        # Check if they supplied a styles_offset even if the count is 0:
        if self.style_offset_count == 0 and self.styles_offset > 0:
            self.log.warning('Styles Offset given, but styleCount is zero.')

        self.string_offsets = []
        self.style_offsets = []
        self.char_buffer = b'' if is_python_3 else bytearray(b'')
        self.styles = []

        # Next, there is a list of string following
        # This is only a list of offsets (4 byte each)
        for i in range(0, self.string_count):
            self.string_offsets.append(unpack('<i', buff.read(4))[0])

        # And a list of styles
        # again, a list of offsets
        for i in range(0, self.style_offset_count):
            self.style_offsets.append(unpack('<i', buff.read(4))[0])

        # FIXME it is probably better to parse n strings and not the size
        size = self.header.size - self.strings_offset

        # if there are styles as well, we do not want to read them too.
        # Only read them, if no
        if self.styles_offset != 0 and self.style_offset_count != 0:
            size = self.styles_offset - self.strings_offset

        # FIXME unaligned
        if (size % 4) != 0:
            self.log.warning('Size of strings is not aligned by four bytes.')

        self.char_buffer = buff.read(size) if is_python_3 else bytearray(buff.read(size))

        if self.styles_offset != 0 and self.style_offset_count != 0:
            size = self.header.size - self.styles_offset

            # FIXME unaligned
            if (size % 4) != 0:
                self.log.warning('Size of styles is not aligned by four bytes.')

            for i in range(0, size // 4):
                self.styles.append(unpack('<i', buff.read(4))[0])

    def get_string(self, idx):
        if idx in self._cache:
            return self._cache[idx]

        if idx < 0 or not self.string_offsets or idx >= len(
                self.string_offsets):
            return ''

        offset = self.string_offsets[idx]

        if self.is_utf8:
            self._cache[idx] = self.decode_utf8(offset)
        else:
            self._cache[idx] = self.decode_utf16(offset)

        return self._cache[idx]

    def get_style(self, idx):
        # FIXME
        return self.styles[idx]

    def decode_utf8(self, offset):
        str_len, skip = self.decode_length(offset, 1)
        offset += skip

        encoded_bytes, skip = self.decode_length(offset, 1)
        offset += skip

        data = self.char_buffer[offset: offset + encoded_bytes]

        return self.decode_bytes(data, 'utf-8', str_len)

    def decode_utf16(self, offset):
        str_len, skip = self.decode_length(offset, 2)
        offset += skip

        encoded_bytes = str_len * 2

        data = self.char_buffer[offset: offset + encoded_bytes]

        return self.decode_bytes(data, 'utf-16', str_len)

    def decode_bytes(self, data, encoding, str_len):
        string = data.decode(encoding, 'replace')
        if len(string) != str_len:
            self.log.warning('invalid decoded string length')
        return string

    def decode_length(self, offset, sizeof_char):
        length = self.char_buffer[offset]

        sizeof_2chars = sizeof_char << 1
        fmt = '<2B' if sizeof_char == 1 else '<2H'

        length1, length2 = unpack(
            fmt, self.char_buffer[offset:(offset + sizeof_2chars)])

        high_bit = 0x80 << (8 * (sizeof_char - 1))

        if (length & high_bit) != 0:
            return (
                (length1 & ~high_bit) << (8 * sizeof_char)
            ) | length2, sizeof_2chars
        else:
            return length1, sizeof_char

    def show(self):
        print('StringBlock(%x, %x, %x, %x, %x, %x' % (
            self.start,
            self.header,
            self.header_size,
            self.chunk_size,
            self.strings_offset,
            self.flags))
        for i in range(0, len(self.string_offsets)):
            print(i, repr(self.get_string(i)))
