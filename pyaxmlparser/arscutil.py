# This file is part of Androguard.
#
# Copyright (C) 2012/2013, Anthony Desnos <desnos at t0t0.fr>
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

import logging
from struct import unpack

try:
    from .utils import format_value
    from . import constants as const

except (ValueError, ImportError):
    from utils import format_value
    import constants as const


class ARSCResTablePackage(object):
    """
    See http://androidxref.com/9.0.0_r3/xref/frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h#861
    """

    def __init__(self, buff, header):
        self.header = header
        self.start = buff.get_idx()
        self.id = unpack("<I", buff.read(4))[0]
        self.name = buff.readNullString(256)
        self.typeStrings = unpack("<I", buff.read(4))[0]
        self.lastPublicType = unpack("<I", buff.read(4))[0]
        self.keyStrings = unpack("<I", buff.read(4))[0]
        self.lastPublicKey = unpack("<I", buff.read(4))[0]
        self.resource_id = self.id << 24

    def get_name(self):
        name = self.name.decode("utf-16", "replace")
        name = name[: name.find("\x00")]
        return name


class ARSCHeader(object):
    """
    Object which contains a Resource Chunk.
    This is an implementation of the `ResChunk_header`.

    It will throw an AssertionError if the header could not be read successfully.

    It is not checked if the data is outside the buffer size nor if the current
    chunk fits into the parent chunk (if any)!

    See http://androidxref.com/9.0.0_r3/xref/frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h#196
    """

    SIZE = 2 + 2 + 4

    def __init__(self, buff):
        self.start = buff.get_idx()
        # Make sure we do not read over the buffer:
        assert (
            buff.size() >= self.start + self.SIZE
        ), "Can not read over the buffer size! Offset={}".format(self.start)
        self._type, self._header_size, self._size = unpack("<HHL", buff.read(self.SIZE))

        # Assert that the read data will fit into the chunk.
        # The total size must be equal or larger than the header size
        assert (
            self._header_size >= self.SIZE
        ), "declared header size is smaller than required size of {}! Offset={}".format(
            self.SIZE, self.start
        )
        assert (
            self._size >= self.SIZE
        ), "declared chunk size is smaller than required size of {}! Offset={}".format(
            self.SIZE, self.start
        )
        assert (
            self._size >= self._header_size
        ), "declared chunk size ({}) is smaller than header size ({})! Offset={}".format(
            self._size, self._header_size, self.start
        )

    @property
    def type(self):
        """
        Type identifier for this chunk
        """
        return self._type

    @property
    def header_size(self):
        """
        Size of the chunk header (in bytes).  Adding this value to
        the address of the chunk allows you to find its associated data
        (if any).
        """
        return self._header_size

    @property
    def size(self):
        """
        Total size of this chunk (in bytes).  This is the chunkSize plus
        the size of any data associated with the chunk.  Adding this value
        to the chunk allows you to completely skip its contents (including
        any child chunks).  If this value is the same as chunkSize, there is
        no data associated with the chunk.
        """
        return self._size

    @property
    def end(self):
        """
        Get the absolute offset inside the file, where the chunk ends.
        This is equal to `ARSCHeader.start + ARSCHeader.size`.
        """
        return self.start + self.size

    def __repr__(self):
        return (
            "<ARSCHeader idx='0x{:08x}' type='{}' header_size='{}' size='{}'>"
        ).format(self.start, self.type, self.header_size, self.size)


class ARSCResTypeSpec(object):
    """
    See http://androidxref.com/9.0.0_r3/xref/frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h#1327
    """

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent
        self.id = unpack("<B", buff.read(1))[0]
        self.res0 = unpack("<B", buff.read(1))[0]
        self.res1 = unpack("<H", buff.read(2))[0]
        assert self.res0 == 0, "res0 must be zero!"
        assert self.res1 == 0, "res1 must be zero!"
        self.entryCount = unpack("<I", buff.read(4))[0]

        self.typespec_entries = []
        for i in range(0, self.entryCount):
            self.typespec_entries.append(unpack("<I", buff.read(4))[0])


class ARSCResType(object):
    """
    See http://androidxref.com/9.0.0_r3/xref/frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h#1364
    """

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.id = unpack("<B", buff.read(1))[0]
        self.flags, = unpack("<B", buff.read(1))
        self.reserved = unpack("<H", buff.read(2))[0]
        assert self.reserved == 0, "reserved must be zero!"
        self.entryCount = unpack("<I", buff.read(4))[0]
        self.entriesStart = unpack("<I", buff.read(4))[0]

        self.resource_id = (0xFF000000 & self.parent.get_resource_id()) | self.id << 16
        self.parent.set_resource_id(self.resource_id)

        self.config = ARSCResTableConfig(buff)

    def get_type(self):
        return self.parent.table_strings.get_string(self.id - 1)

    def get_package_name(self):
        return self.parent.get_package_name()

    def __repr__(self):
        return "ARSCResType(%x, %x, %x, %x, %x, %x, %x, %s)" % (
            self.start,
            self.id,
            self.flags,
            self.reserved,
            self.entryCount,
            self.entriesStart,
            self.resource_id,
            "table:" + self.parent.table_strings.get_string(self.id - 1),
        )


class ARSCResTableConfig(object):
    """
    ARSCResTableConfig contains the configuration for specific resource selection.
    This is used on the device to determine which resources should be loaded
    based on different properties of the device like locale or displaysize.

    See the definition of ResTable_config in
    http://androidxref.com/9.0.0_r3/xref/frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h#911
    """

    @classmethod
    def default_config(cls):
        if not hasattr(cls, "DEFAULT"):
            cls.DEFAULT = ARSCResTableConfig(None)
        return cls.DEFAULT

    def __init__(self, buff=None, **kwargs):
        self.log = logging.getLogger("pyaxmlparser.arscutil")
        if buff is not None:
            self.start = buff.get_idx()

            # uint32_t
            self.size = unpack("<I", buff.read(4))[0]

            # union: uint16_t mcc, uint16_t mnc
            # 0 means any
            self.imsi = unpack("<I", buff.read(4))[0]

            # uint32_t as chars \0\0 means any
            # either two 7bit ASCII representing the ISO-639-1 language code
            # or a single 16bit LE value representing ISO-639-2 3 letter code
            self.locale = unpack("<I", buff.read(4))[0]

            # struct of:
            # uint8_t orientation
            # uint8_t touchscreen
            # uint8_t density
            self.screen_type = unpack("<I", buff.read(4))[0]

            # struct of
            # uint8_t keyboard
            # uint8_t navigation
            # uint8_t inputFlags
            # uint8_t inputPad0
            self.input = unpack("<I", buff.read(4))[0]

            # struct of
            # uint16_t screenWidth
            # uint16_t screenHeight
            self.screen_size = unpack("<I", buff.read(4))[0]

            # struct of
            # uint16_t sdkVersion
            # uint16_t minorVersion  which should be always 0, as the meaning is not defined
            self.version = unpack("<I", buff.read(4))[0]

            # The next three fields seems to be optional
            if self.size >= 32:
                # struct of
                # uint8_t screenLayout
                # uint8_t uiMode
                # uint16_t smallestScreenWidthDp
                self.screen_config, = unpack("<I", buff.read(4))
            else:
                self.log.debug(
                    "This file does not have a screen_config! size={}".format(self.size)
                )
                self.screen_config = 0

            if self.size >= 36:
                # struct of
                # uint16_t screenWidthDp
                # uint16_t screenHeightDp
                self.screen_size_dp, = unpack("<I", buff.read(4))
            else:
                self.log.debug(
                    "This file does not have a screenSizeDp! size={}".format(self.size)
                )
                self.screen_size_dp = 0

            if self.size >= 40:
                # struct of
                # uint8_t screenLayout2
                # uint8_t colorMode
                # uint16_t screenConfigPad2
                self.screen_config_2, = unpack("<I", buff.read(4))
            else:
                self.log.debug(
                    "This file does not have a screen_config2! size={}".format(
                        self.size
                    )
                )
                self.screen_config_2 = 0

            self.exceeding_size = self.size - (buff.tell() - self.start)
            if self.exceeding_size > 0:
                self.log.debug("Skipping padding bytes!")
                self.padding = buff.read(self.exceeding_size)

        else:
            self.start = 0
            self.size = 0
            self.imsi = ((kwargs.pop("mcc", 0) & 0xFFFF) << 0) + (
                (kwargs.pop("mnc", 0) & 0xFFFF) << 16
            )

            self.locale = 0
            for char_ix, char in kwargs.pop("locale", "")[0:4]:
                self.locale += ord(char) << (char_ix * 8)

            self.screen_type = (
                ((kwargs.pop("orientation", 0) & 0xFF) << 0)
                + ((kwargs.pop("touchscreen", 0) & 0xFF) << 8)
                + ((kwargs.pop("density", 0) & 0xFFFF) << 16)
            )

            self.input = (
                ((kwargs.pop("keyboard", 0) & 0xFF) << 0)
                + ((kwargs.pop("navigation", 0) & 0xFF) << 8)
                + ((kwargs.pop("inputFlags", 0) & 0xFF) << 16)
                + ((kwargs.pop("inputPad0", 0) & 0xFF) << 24)
            )

            self.screen_size = ((kwargs.pop("screenWidth", 0) & 0xFFFF) << 0) + (
                (kwargs.pop("screenHeight", 0) & 0xFFFF) << 16
            )

            self.version = ((kwargs.pop("sdkVersion", 0) & 0xFFFF) << 0) + (
                (kwargs.pop("minorVersion", 0) & 0xFFFF) << 16
            )

            self.screen_config = (
                ((kwargs.pop("screenLayout", 0) & 0xFF) << 0)
                + ((kwargs.pop("uiMode", 0) & 0xFF) << 8)
                + ((kwargs.pop("smallestScreenWidthDp", 0) & 0xFFFF) << 16)
            )

            self.screen_size_dp = ((kwargs.pop("screenWidthDp", 0) & 0xFFFF) << 0) + (
                (kwargs.pop("screenHeightDp", 0) & 0xFFFF) << 16
            )

            # TODO add this some day...
            self.screen_config_2 = 0

            self.exceeding_size = 0

    @staticmethod
    def unpack_language_or_region(char_in, char_base):
        char_out = ""
        if char_in[0] & 0x80:
            first = char_in[1] & 0x1F
            second = ((char_in[1] & 0xE0) >> 5) + ((char_in[0] & 0x03) << 3)
            third = (char_in[0] & 0x7C) >> 2
            char_out += chr(first + char_base)
            char_out += chr(second + char_base)
            char_out += chr(third + char_base)
        else:
            if char_in[0]:
                char_out += chr(char_in[0])
            if char_in[1]:
                char_out += chr(char_in[1])
        return char_out

    def get_language_and_region(self):
        """
        Returns the combined language+region string or \x00\x00 for the default locale
        :return:
        """
        if self.locale != 0:
            language = self.unpack_language_or_region(
                [self.locale & 0xFF, (self.locale & 0xFF00) >> 8], ord("a")
            )
            region = self.unpack_language_or_region(
                [(self.locale & 0xFF0000) >> 16, (self.locale & 0xFF000000) >> 24],
                ord("0"),
            )
            return "{}-r{}".format(language, region) if region else language
        return "\x00\x00"

    def get_config_name_friendly(self):
        """
        Here for legacy reasons.

        use :meth:`~get_qualifier` instead.
        """
        return self.get_qualifier()

    def get_qualifier(self):
        """
        Return resource name qualifier for the current configuration.
        for example
        * `ldpi-v4`
        * `hdpi-v4`

        All possible qualifiers are listed in table 2 of https://developer.android.com/guide
        /topics/resources/providing-resources

        FIXME: This name might not have all properties set!
        :return: str
        """
        res = []

        mcc = self.imsi & 0xFFFF
        mnc = (self.imsi & 0xFFFF0000) >> 16
        if mcc != 0:
            res.append("mcc%d" % mcc)
        if mnc != 0:
            res.append("mnc%d" % mnc)

        if self.locale != 0:
            res.append(self.get_language_and_region())

        screen_layout = self.screen_config & 0xFF
        if (screen_layout & const.MASK_LAYOUTDIR) != 0:
            if screen_layout & const.MASK_LAYOUTDIR == const.LAYOUTDIR_LTR:
                res.append("ldltr")
            elif screen_layout & const.MASK_LAYOUTDIR == const.LAYOUTDIR_RTL:
                res.append("ldrtl")
            else:
                res.append("layoutDir_%d" % (screen_layout & const.MASK_LAYOUTDIR))

        smallest_screen_width_dp = (self.screen_config & 0xFFFF0000) >> 16
        if smallest_screen_width_dp != 0:
            res.append("sw%ddp" % smallest_screen_width_dp)

        screen_width_dp = self.screen_size_dp & 0xFFFF
        screen_height_dp = (self.screen_size_dp & 0xFFFF0000) >> 16
        if screen_width_dp != 0:
            res.append("w%ddp" % screen_width_dp)
        if screen_height_dp != 0:
            res.append("h%ddp" % screen_height_dp)

        if (screen_layout & const.MASK_SCREENSIZE) != const.SCREENSIZE_ANY:
            if screen_layout & const.MASK_SCREENSIZE == const.SCREENSIZE_SMALL:
                res.append("small")
            elif screen_layout & const.MASK_SCREENSIZE == const.SCREENSIZE_NORMAL:
                res.append("normal")
            elif screen_layout & const.MASK_SCREENSIZE == const.SCREENSIZE_LARGE:
                res.append("large")
            elif screen_layout & const.MASK_SCREENSIZE == const.SCREENSIZE_XLARGE:
                res.append("xlarge")
            else:
                res.append(
                    "screenLayoutSize_%d" % (screen_layout & const.MASK_SCREENSIZE)
                )
        if (screen_layout & const.MASK_SCREENLONG) != 0:
            if screen_layout & const.MASK_SCREENLONG == const.SCREENLONG_NO:
                res.append("notlong")
            elif screen_layout & const.MASK_SCREENLONG == const.SCREENLONG_YES:
                res.append("long")
            else:
                res.append(
                    "screenLayoutLong_%d" % (screen_layout & const.MASK_SCREENLONG)
                )

        density = (self.screen_type & 0xFFFF0000) >> 16
        if density != const.DENSITY_DEFAULT:
            if density == const.DENSITY_LOW:
                res.append("ldpi")
            elif density == const.DENSITY_MEDIUM:
                res.append("mdpi")
            elif density == const.DENSITY_TV:
                res.append("tvdpi")
            elif density == const.DENSITY_HIGH:
                res.append("hdpi")
            elif density == const.DENSITY_XHIGH:
                res.append("xhdpi")
            elif density == const.DENSITY_XXHIGH:
                res.append("xxhdpi")
            elif density == const.DENSITY_XXXHIGH:
                res.append("xxxhdpi")
            elif density == const.DENSITY_NONE:
                res.append("nodpi")
            elif density == const.DENSITY_ANY:
                res.append("anydpi")
            else:
                res.append("%ddpi" % density)

        touchscreen = (self.screen_type & 0xFF00) >> 8
        if touchscreen != const.TOUCHSCREEN_ANY:
            if touchscreen == const.TOUCHSCREEN_NOTOUCH:
                res.append("notouch")
            elif touchscreen == const.TOUCHSCREEN_FINGER:
                res.append("finger")
            elif touchscreen == const.TOUCHSCREEN_STYLUS:
                res.append("stylus")
            else:
                res.append("touchscreen_%d" % touchscreen)

        screen_size = self.screen_size
        if screen_size != 0:
            screen_width = self.screen_size & 0xFFFF
            screen_height = (self.screen_size & 0xFFFF0000) >> 16
            res.append("%dx%d" % (screen_width, screen_height))

        version = self.version
        if version != 0:
            sdk_version = self.version & 0xFFFF
            minor_version = (self.version & 0xFFFF0000) >> 16
            res.append("v%d" % sdk_version)
            if minor_version != 0:
                res.append(".%d" % minor_version)

        return "-".join(res)

    def get_language(self):
        x = self.locale & 0x0000FFFF
        return chr(x & 0x00FF) + chr((x & 0xFF00) >> 8)

    def get_country(self):
        x = (self.locale & 0xFFFF0000) >> 16
        return chr(x & 0x00FF) + chr((x & 0xFF00) >> 8)

    def get_density(self):
        x = (self.screen_type >> 16) & 0xFFFF
        return x

    def is_default(self):
        """
        Test if this is a default resource, which matches all

        This is indicated that all fields are zero.
        :return: True if default, False otherwise
        """
        return all(map(lambda x: x == 0, self.get_tuple()))

    def get_tuple(self):
        return (
            self.imsi,
            self.locale,
            self.screen_type,
            self.input,
            self.screen_size,
            self.version,
            self.screen_config,
            self.screen_size_dp,
            self.screen_config_2,
        )

    def __hash__(self):
        return hash(self.get_tuple())

    def __eq__(self, other):
        return self.get_tuple() == other.get_tuple()

    def __repr__(self):
        return "<ARSCResTableConfig '{}'='{}'>".format(
            self.get_qualifier(), repr(self.get_tuple())
        )


class ARSCResTableEntry(object):
    """
    See https://github.com/LineageOS/android_frameworks_base/blob/
    df2898d9ce306bb2fe922d3beaa34a9cf6873d27/include/androidfw/ResourceTypes.h#L1370
    """

    FLAG_COMPLEX = 1
    FLAG_PUBLIC = 2
    FLAG_WEAK = 4

    def __init__(self, buff, resource_id, parent=None):
        self.start = buff.get_idx()
        self.resource_id = resource_id
        self.parent = parent
        self.size = unpack("<H", buff.read(2))[0]
        self.flags = unpack("<H", buff.read(2))[0]
        self.index = unpack("<I", buff.read(4))[0]

        if self.is_complex:
            self.item = ARSCComplex(buff, parent)
        else:
            # If FLAG_COMPLEX is not set, a Res_value structure will follow
            self.key = ARSCResStringPoolRef(buff, self.parent)

    def get_index(self):
        return self.index

    def get_value(self):
        return self.parent.key_strings.get_string(self.index)

    def get_key_data(self):
        return self.key.get_data_value()

    def is_public(self):
        return (self.flags & self.FLAG_PUBLIC) != 0

    @property
    def is_complex(self):
        return (self.flags & self.FLAG_COMPLEX) != 0

    def is_weak(self):
        return (self.flags & self.FLAG_WEAK) != 0

    def __repr__(self):
        return (
            "<ARSCResTableEntry idx='0x{:08x}' mResId='0x{:08x}' size='{}' "
            "flags='0x{:02x}' index='0x{:x}' holding={}>"
        ).format(
            self.start,
            self.resource_id,
            self.size,
            self.flags,
            self.index,
            self.item if self.is_complex else self.key,
        )


class ARSCComplex(object):
    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.id_parent = unpack("<I", buff.read(4))[0]
        self.count = unpack("<I", buff.read(4))[0]

        self.items = []
        for i in range(0, self.count):
            self.items.append(
                (unpack("<I", buff.read(4))[0], ARSCResStringPoolRef(buff, self.parent))
            )

    def __repr__(self):
        return "<ARSCComplex idx='0x{:08x}' parent='{}' count='{}'>".format(
            self.start, self.id_parent, self.count
        )


class ARSCResStringPoolRef(object):
    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.size, = unpack("<H", buff.read(2))
        self.res0, = unpack("<B", buff.read(1))
        assert self.res0 == 0, "res0 must be always zero!"
        self.data_type = unpack("<B", buff.read(1))[0]
        self.data = unpack("<I", buff.read(4))[0]

    def get_data_value(self):
        return self.parent.string_pool_main.get_string(self.data)

    def get_data(self):
        return self.data

    def get_data_type(self):
        return self.data_type

    def get_data_type_string(self):
        return const.TYPE_TABLE[self.data_type]

    def format_value(self):
        return format_value(
            self.data_type, self.data, self.parent.string_pool_main.get_string
        )

    def is_reference(self):
        return self.data_type == const.TYPE_REFERENCE

    def __repr__(self):
        return "<ARSCResStringPoolRef idx='0x{:08x}' size='{}' type='{}' data='0x{:08x}'>".format(
            self.start,
            self.size,
            const.TYPE_TABLE.get(self.data_type, "0x%x" % self.data_type),
            self.data,
        )


def get_arsc_info(arscobj):
    """
    Return a string containing all resources packages ordered by packagename, locale and type.

    :param arscobj: :class:`~ARSCParser`
    :return: a string
    """
    buff = ""
    for package in arscobj.packages_names():
        buff += package + ":\n"
        for locale in arscobj.get_locales(package):
            buff += "\t" + repr(locale) + ":\n"
            for ttype in arscobj.get_types(package, locale):
                buff += "\t\t" + ttype + ":\n"
                try:
                    tmp_buff = (
                        getattr(arscobj, "get_" + ttype + "_resources")(package, locale)
                        .decode("utf-8", "replace")
                        .split("\n")
                    )
                    for i in tmp_buff:
                        buff += "\t\t\t" + i + "\n"
                except AttributeError:
                    pass
    return buff
