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

from struct import unpack
from warnings import warn
import pyaxmlparser.constants as const
from pyaxmlparser.utils import format_value


class ARSCResTablePackage(object):
    def __init__(self, buff, header):
        self.header = header
        self.start = buff.get_idx()
        self.id = unpack('<I', buff.read(4))[0]
        self.name = buff.readNullString(256)
        self.typeStrings = unpack('<I', buff.read(4))[0]
        self.lastPublicType = unpack('<I', buff.read(4))[0]
        self.keyStrings = unpack('<I', buff.read(4))[0]
        self.lastPublicKey = unpack('<I', buff.read(4))[0]
        self.mResId = self.id << 24

    def get_name(self):
        name = self.name.decode("utf-16", 'replace')
        name = name[:name.find("\x00")]
        return name


class ARSCHeader(object):
    SIZE = 2 + 2 + 4

    def __init__(self, buff):
        self.start = buff.get_idx()
        self.type = unpack('<h', buff.read(2))[0]
        self.header_size = unpack('<h', buff.read(2))[0]
        self.size = unpack('<I', buff.read(4))[0]

    def __repr__(self):
        return (
            "<ARSCHeader idx='0x{:08x}' type='{}' header_size='{}' size='{}'>"
        ).format(self.start, self.type, self.header_size, self.size)


class ARSCResTypeSpec(object):
    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent
        self.id = unpack('<b', buff.read(1))[0]
        self.res0 = unpack('<b', buff.read(1))[0]
        self.res1 = unpack('<h', buff.read(2))[0]
        self.entryCount = unpack('<I', buff.read(4))[0]

        self.typespec_entries = []
        for i in range(0, self.entryCount):
            self.typespec_entries.append(unpack('<I', buff.read(4))[0])


class ARSCResType(object):
    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent
        self.id = unpack('<b', buff.read(1))[0]
        self.res0 = unpack('<b', buff.read(1))[0]
        self.res1 = unpack('<h', buff.read(2))[0]
        self.entryCount = unpack('<i', buff.read(4))[0]
        self.entriesStart = unpack('<i', buff.read(4))[0]
        self.mResId = (0xff000000 & self.parent.get_mResId()) | self.id << 16
        self.parent.set_mResId(self.mResId)

        self.config = ARSCResTableConfig(buff)

    def get_type(self):
        return self.parent.mTableStrings.getString(self.id - 1)

    def get_package_name(self):
        return self.parent.get_package_name()

    def __repr__(self):
        return "ARSCResType(%x, %x, %x, %x, %x, %x, %x, %s)" % (
            self.start,
            self.id,
            self.res0,
            self.res1,
            self.entryCount,
            self.entriesStart,
            self.mResId,
            "table:" + self.parent.mTableStrings.getString(self.id - 1)
        )


class ARSCResTableConfig(object):
    @classmethod
    def default_config(cls):
        if not hasattr(cls, 'DEFAULT'):
            cls.DEFAULT = ARSCResTableConfig(None)
        return cls.DEFAULT

    def __init__(self, buff=None, **kwargs):
        """
        ARSCResTableConfig contains the configuration for specific resource
        selection.
        This is used on the device to determine which resources should be loaded
        based on different properties of the device like locale or displaysize.
        See the definiton of ResTable_config in
    platform_frameworks_base/libs/androidfw/include/androidfw/ResourceTypes.h
        :param buff:
        :param kwargs:
        """
        if buff is not None:
            self.start = buff.get_idx()

            # uint32_t
            self.size = unpack('<I', buff.read(4))[0]

            # union: uint16_t mcc, uint16_t mnc
            # 0 means any
            self.imsi = unpack('<I', buff.read(4))[0]

            # uint32_t as chars \0\0 means any
            # either two 7bit ASCII representing the ISO-639-1 language code
            # or a single 16bit LE value representing ISO-639-2 3 letter code
            self.locale = unpack('<I', buff.read(4))[0]

            # struct of:
            # uint8_t orientation
            # uint8_t touchscreen
            # uint8_t density
            self.screenType = unpack('<I', buff.read(4))[0]

            # struct of
            # uint8_t keyboard
            # uint8_t navigation
            # uint8_t inputFlags
            # uint8_t inputPad0
            self.input = unpack('<I', buff.read(4))[0]

            # struct of
            # uint16_t screenWidth
            # uint16_t screenHeight
            self.screenSize = unpack('<I', buff.read(4))[0]

            # struct of
            # uint16_t sdkVersion
            # uint16_t minorVersion  which should be always 0, as the meaning
            # is not defined
            self.version = unpack('<I', buff.read(4))[0]

            self.screenConfig = 0
            self.screenSizeDp = 0

            if self.size >= 32:
                # FIXME: is this really not always there?
                # struct of
                # uint8_t screenLayout
                # uint8_t uiMode
                # uint16_t smallestScreenWidthDp
                self.screenConfig = unpack('<I', buff.read(4))[0]

                if self.size >= 36:
                    # FIXME is this really not always there?
                    # struct of
                    # uint16_t screenWidthDp
                    # uint16_t screenHeightDp
                    self.screenSizeDp = unpack('<I', buff.read(4))[0]

            self.exceedingSize = self.size - 36
            if self.exceedingSize > 0:
                warn("Skipping padding bytes!")
                self.padding = buff.read(self.exceedingSize)

        # TODO there is screenConfig2

        else:
            self.start = 0
            self.size = 0
            self.imsi = \
                ((kwargs.pop('mcc', 0) & 0xffff) << 0) + \
                ((kwargs.pop('mnc', 0) & 0xffff) << 16)

            self.locale = 0
            for char_ix, char in kwargs.pop('locale', "")[0:4]:
                self.locale += (ord(char) << (char_ix * 8))

            self.screenType = \
                ((kwargs.pop('orientation', 0) & 0xff) << 0) + \
                ((kwargs.pop('touchscreen', 0) & 0xff) << 8) + \
                ((kwargs.pop('density', 0) & 0xffff) << 16)

            self.input = \
                ((kwargs.pop('keyboard', 0) & 0xff) << 0) + \
                ((kwargs.pop('navigation', 0) & 0xff) << 8) + \
                ((kwargs.pop('inputFlags', 0) & 0xff) << 16) + \
                ((kwargs.pop('inputPad0', 0) & 0xff) << 24)

            self.screenSize = \
                ((kwargs.pop('screenWidth', 0) & 0xffff) << 0) + \
                ((kwargs.pop('screenHeight', 0) & 0xffff) << 16)

            self.version = \
                ((kwargs.pop('sdkVersion', 0) & 0xffff) << 0) + \
                ((kwargs.pop('minorVersion', 0) & 0xffff) << 16)

            self.screenConfig = \
                ((kwargs.pop('screenLayout', 0) & 0xff) << 0) + \
                ((kwargs.pop('uiMode', 0) & 0xff) << 8) + \
                ((kwargs.pop('smallestScreenWidthDp', 0) & 0xffff) << 16)

            self.screenSizeDp = \
                ((kwargs.pop('screenWidthDp', 0) & 0xffff) << 0) + \
                ((kwargs.pop('screenHeightDp', 0) & 0xffff) << 16)

            self.exceedingSize = 0

    def _unpack_language_or_region(self, char_in, char_base):
        char_out = ""
        if char_in[0] & 0x80:
            first = char_in[1] & 0x1f
            second = ((char_in[1] & 0xe0) >> 5) + ((char_in[0] & 0x03) << 3)
            third = (char_in[0] & 0x7c) >> 2
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
        if self.locale != 0:
            _language = self._unpack_language_or_region(
                [self.locale & 0xff, (self.locale & 0xff00) >> 8, ], ord('a'))
            _region = self._unpack_language_or_region(
                [
                    (self.locale & 0xff0000) >> 16,
                    (self.locale & 0xff000000) >> 24,
                ],
                ord('0')
            )
            return (_language + "-r" + _region) if _region else _language
        return ""

    def get_config_name_friendly(self):
        res = []

        mcc = self.imsi & 0xFFFF
        mnc = (self.imsi & 0xFFFF0000) >> 16
        if mcc != 0:
            res.append("mcc%d" % mcc)
        if mnc != 0:
            res.append("mnc%d" % mnc)

        if self.locale != 0:
            res.append(self.get_language_and_region())

        screenLayout = self.screenConfig & 0xff
        if (screenLayout & const.MASK_LAYOUTDIR) != 0:
            if screenLayout & const.MASK_LAYOUTDIR == const.LAYOUTDIR_LTR:
                res.append("ldltr")
            elif screenLayout & const.MASK_LAYOUTDIR == const.LAYOUTDIR_RTL:
                res.append("ldrtl")
            else:
                res.append(
                    "layoutDir_%d" % (screenLayout & const.MASK_LAYOUTDIR))

        smallestScreenWidthDp = (self.screenConfig & 0xFFFF0000) >> 16
        if smallestScreenWidthDp != 0:
            res.append("sw%ddp" % smallestScreenWidthDp)

        screenWidthDp = self.screenSizeDp & 0xFFFF
        screenHeightDp = (self.screenSizeDp & 0xFFFF0000) >> 16
        if screenWidthDp != 0:
            res.append("w%ddp" % screenWidthDp)
        if screenHeightDp != 0:
            res.append("h%ddp" % screenHeightDp)

        if (screenLayout & const.MASK_SCREENSIZE) != const.SCREENSIZE_ANY:
            if screenLayout & const.MASK_SCREENSIZE == const.SCREENSIZE_SMALL:
                res.append("small")
            elif screenLayout & \
                    const.MASK_SCREENSIZE == const.SCREENSIZE_NORMAL:
                res.append("normal")
            elif screenLayout & \
                    const.MASK_SCREENSIZE == const.SCREENSIZE_LARGE:
                res.append("large")
            elif screenLayout & \
                    const.MASK_SCREENSIZE == const.SCREENSIZE_XLARGE:
                res.append("xlarge")
            else:
                res.append(
                    "screenLayoutSize_%d" % (
                        screenLayout & const.MASK_SCREENSIZE
                    )
                )
        if (screenLayout & const.MASK_SCREENLONG) != 0:
            if screenLayout & const.MASK_SCREENLONG == const.SCREENLONG_NO:
                res.append("notlong")
            elif screenLayout & const.MASK_SCREENLONG == const.SCREENLONG_YES:
                res.append("long")
            else:
                res.append(
                    "screenLayoutLong_%d" % (
                        screenLayout & const.MASK_SCREENLONG
                    )
                )

        density = (self.screenType & 0xffff0000) >> 16
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
                res.append("%ddpi" % (density))

        touchscreen = (self.screenType & 0xff00) >> 8
        if touchscreen != const.TOUCHSCREEN_ANY:
            if touchscreen == const.TOUCHSCREEN_NOTOUCH:
                res.append("notouch")
            elif touchscreen == const.TOUCHSCREEN_FINGER:
                res.append("finger")
            elif touchscreen == const.TOUCHSCREEN_STYLUS:
                res.append("stylus")
            else:
                res.append("touchscreen_%d" % touchscreen)

        screenSize = self.screenSize
        if screenSize != 0:
            screenWidth = self.screenSize & 0xffff
            screenHeight = (self.screenSize & 0xffff0000) >> 16
            res.append("%dx%d" % (screenWidth, screenHeight))

        version = self.version
        if version != 0:
            sdkVersion = self.version & 0xffff
            minorVersion = (self.version & 0xffff0000) >> 16
            res.append("v%d" % sdkVersion)
            if minorVersion != 0:
                res.append(".%d" % minorVersion)

        return "-".join(res)

    def get_language(self):
        x = self.locale & 0x0000ffff
        return chr(x & 0x00ff) + chr((x & 0xff00) >> 8)

    def get_country(self):
        x = (self.locale & 0xffff0000) >> 16
        return chr(x & 0x00ff) + chr((x & 0xff00) >> 8)

    def get_density(self):
        x = ((self.screenType >> 16) & 0xffff)
        return x

    def _get_tuple(self):
        return (
            self.imsi,
            self.locale,
            self.screenType,
            self.input,
            self.screenSize,
            self.version,
            self.screenConfig,
            self.screenSizeDp,
        )

    def __hash__(self):
        return hash(self._get_tuple())

    def __eq__(self, other):
        return self._get_tuple() == other._get_tuple()

    def __repr__(self):
        return "<ARSCResTableConfig '{}'>".format(repr(self._get_tuple()))


class ARSCResTableEntry(object):
    FLAG_COMPLEX = 1
    FLAG_PUBLIC = 2
    FLAG_WEAK = 4

    def __init__(self, buff, mResId, parent=None):
        self.start = buff.get_idx()
        self.mResId = mResId
        self.parent = parent
        self.size = unpack('<H', buff.read(2))[0]
        self.flags = unpack('<H', buff.read(2))[0]
        self.index = unpack('<I', buff.read(4))[0]

        if self.is_complex():
            self.item = ARSCComplex(buff, parent)
        else:
            # If FLAG_COMPLEX is not set, a Res_value structure will follow
            self.key = ARSCResStringPoolRef(buff, self.parent)

    def get_index(self):
        return self.index

    def get_value(self):
        return self.parent.mKeyStrings.getString(self.index)

    def get_key_data(self):
        return self.key.get_data_value()

    def is_public(self):
        return (self.flags & self.FLAG.PUBLIC) != 0

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
            self.mResId,
            self.size,
            self.flags,
            self.index,
            self.item if self.is_complex() else self.key)


class ARSCComplex(object):
    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.id_parent = unpack('<I', buff.read(4))[0]
        self.count = unpack('<I', buff.read(4))[0]

        self.items = []
        for i in range(0, self.count):
            self.items.append((unpack('<I', buff.read(4))[0],
                               ARSCResStringPoolRef(buff, self.parent)))

    def __repr__(self):
        return "<ARSCComplex idx='0x{:08x}' parent='{}' count='{}'>".format(
            self.start, self.id_parent, self.count)


class ARSCResStringPoolRef(object):
    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.size, = unpack("<H", buff.read(2))
        self.res0, = unpack("<B", buff.read(1))
        assert self.res0 == 0, "res0 must be always zero!"
        self.data_type = unpack('<B', buff.read(1))[0]
        self.data = unpack('<I', buff.read(4))[0]

    def get_data_value(self):
        return self.parent.stringpool_main.getString(self.data)

    def get_data(self):
        return self.data

    def get_data_type(self):
        return self.data_type

    def get_data_type_string(self):
        return const.TYPE_TABLE[self.data_type]

    def format_value(self):
        return format_value(
            self.data_type,
            self.data,
            self.parent.stringpool_main.getString
        )

    def is_reference(self):
        return self.data_type == const.TYPE_REFERENCE

    def __repr__(self):
        return (
            "<ARSCResStringPoolRef idx='0x{:08x}' size='{}' "
            "type='{}' data='0x{:08x}'>"
        ).format(
            self.start,
            self.size,
            const.TYPE_TABLE.get(self.data_type, "0x%x" % self.data_type),
            self.data)
        return self.data_type


def get_arsc_info(arscobj):
    """
    Return a string containing all resources packages ordered by packagename,
    locale and type.
    :param arscobj: :class:`~ARSCParser`
    :return: a string
    """
    buff = ""
    for package in arscobj.get_packages_names():
        buff += package + ":\n"
        for locale in arscobj.get_locales(package):
            buff += "\t" + repr(locale) + ":\n"
            for ttype in arscobj.get_types(package, locale):
                buff += "\t\t" + ttype + ":\n"
                try:
                    tmp_buff = getattr(arscobj, "get_" + ttype + "_resources")(
                        package, locale).decode("utf-8", 'replace').split("\n")
                    for i in tmp_buff:
                        buff += "\t\t\t" + i + "\n"
                except AttributeError:
                    pass
    return buff
