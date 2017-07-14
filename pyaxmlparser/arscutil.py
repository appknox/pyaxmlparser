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
from pyaxmlparser.utils import _range


class ARSCResTablePackage(object):

    def __init__(self, buff):
        self.start = buff.get_idx()
        self.id = unpack('<i', buff.read(4))[0]
        self.name = buff.readNullString(256)
        self.typeStrings = unpack('<i', buff.read(4))[0]
        self.lastPublicType = unpack('<i', buff.read(4))[0]
        self.keyStrings = unpack('<i', buff.read(4))[0]
        self.lastPublicKey = unpack('<i', buff.read(4))[0]
        self.mResId = self.id << 24

        # print "ARSCResTablePackage", hex(self.start), hex(self.id),
        # hex(self.mResId), repr(self.name.decode("utf-16", errors='replace')),
        # hex(self.typeStrings), hex(self.lastPublicType),
        # hex(self.keyStrings), hex(self.lastPublicKey)

    def get_name(self):
        name = self.name.decode("utf-16", 'replace')
        name = name[:name.find("\x00")]
        return name


class ARSCHeader(object):

    def __init__(self, buff):
        self.start = buff.get_idx()
        self.type = unpack('<h', buff.read(2))[0]
        self.header_size = unpack('<h', buff.read(2))[0]
        self.size = unpack('<i', buff.read(4))[0]


class ARSCResTypeSpec(object):

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent
        self.id = unpack('<b', buff.read(1))[0]
        self.res0 = unpack('<b', buff.read(1))[0]
        self.res1 = unpack('<h', buff.read(2))[0]
        self.entryCount = unpack('<i', buff.read(4))[0]

        # print "ARSCResTypeSpec", hex(self.start), hex(self.id),
        # hex(self.res0), hex(self.res1), hex(self.entryCount), "table:" +
        # self.parent.mTableStrings.getString(self.id - 1)

        self.typespec_entries = []
        for i in _range(0, self.entryCount):
            self.typespec_entries.append(unpack('<i', buff.read(4))[0])


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

        # print "ARSCResType", hex(self.start), hex(self.id), hex(self.res0),
        # hex(self.res1), hex(self.entryCount), hex(self.entriesStart),
        # hex(self.mResId), "table:" +
        # self.parent.mTableStrings.getString(self.id - 1)

        self.config = ARSCResTableConfig(buff)

    def get_type(self):
        return self.parent.mTableStrings.getString(self.id - 1)


class ARSCResTableConfig(object):

    def __init__(self, buff):
        self.start = buff.get_idx()
        self.size = unpack('<i', buff.read(4))[0]
        self.imsi = unpack('<i', buff.read(4))[0]
        self.locale = unpack('<i', buff.read(4))[0]
        self.screenType = unpack('<i', buff.read(4))[0]
        self.input = unpack('<i', buff.read(4))[0]
        self.screenSize = unpack('<i', buff.read(4))[0]
        self.version = unpack('<i', buff.read(4))[0]

        self.screenConfig = 0
        self.screenSizeDp = 0

        if self.size >= 32:
            self.screenConfig = unpack('<i', buff.read(4))[0]

            if self.size >= 36:
                self.screenSizeDp = unpack('<i', buff.read(4))[0]

        self.exceedingSize = self.size - 36
        if self.exceedingSize > 0:
            self.padding = buff.read(self.exceedingSize)

        # print "ARSCResTableConfig", hex(self.start), hex(self.size),
        # hex(self.imsi), hex(self.locale), repr(self.get_language()),
        # repr(self.get_country()), hex(self.screenType), hex(self.input),
        # hex(self.screenSize), hex(self.version), hex(self.screenConfig),
        # hex(self.screenSizeDp)

    def get_language(self):
        x = self.locale & 0x0000ffff
        return chr(x & 0x00ff) + chr((x & 0xff00) >> 8)

    def get_country(self):
        x = (self.locale & 0xffff0000) >> 16
        return chr(x & 0x00ff) + chr((x & 0xff00) >> 8)


class ARSCResTableEntry(object):

    def __init__(self, buff, mResId, parent=None):
        self.start = buff.get_idx()
        self.mResId = mResId
        self.parent = parent
        self.size = unpack('<h', buff.read(2))[0]
        self.flags = unpack('<h', buff.read(2))[0]
        self.index = unpack('<i', buff.read(4))[0]

        # print "ARSCResTableEntry", hex(self.start), hex(self.mResId),
        # hex(self.size), hex(self.flags), hex(self.index), self.is_complex()#,
        # hex(self.mResId)

        if self.flags & 1:
            self.item = ARSCComplex(buff, parent)
        else:
            self.key = ARSCResStringPoolRef(buff, self.parent)

    def get_index(self):
        return self.index

    def get_value(self):
        return self.parent.mKeyStrings.getString(self.index)

    def get_key_data(self):
        return self.key.get_data_value()

    def is_public(self):
        return self.flags == 0 or self.flags == 2

    def is_complex(self):
        return (self.flags & 1) == 1


class ARSCComplex(object):

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.id_parent = unpack('<i', buff.read(4))[0]
        self.count = unpack('<i', buff.read(4))[0]

        self.items = []
        for i in _range(0, self.count):
            self.items.append((unpack('<i', buff.read(4))[
                              0], ARSCResStringPoolRef(buff, self.parent)))

        # print "ARSCComplex", hex(self.start), self.id_parent, self.count,
        # repr(self.parent.mKeyStrings.getString(self.id_parent))


class ARSCResStringPoolRef(object):

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.skip_bytes = buff.read(3)
        self.data_type = unpack('<b', buff.read(1))[0]
        self.data = unpack('<i', buff.read(4))[0]

        # print "ARSCResStringPoolRef", hex(self.start), hex(self.data_type),
        # hex(self.data)#, "key:" +
        # self.parent.mKeyStrings.getString(self.index),
        # self.parent.stringpool_main.getString(self.data)

    def get_data_value(self):
        return self.parent.stringpool_main.getString(self.data)

    def get_data(self):
        return self.data

    def get_data_type(self):
        return self.data_type


def get_arsc_info(arscobj):
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
