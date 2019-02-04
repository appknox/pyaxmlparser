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

from struct import unpack, pack


class SV(object):

    def __init__(self, size, buff):
        self.__size = size
        self.__value = unpack(self.__size, buff)[0]

    def _get(self):
        return pack(self.__size, self.__value)

    def __str__(self):
        return "0x%x" % self.__value

    def __int__(self):
        return self.__value

    def get_value_buff(self):
        return self._get()

    def get_value(self):
        return self.__value

    def set_value(self, attr):
        self.__value = attr


class SVs(object):

    def __init__(self, size, ntuple, buff):
        self.__size = size

        self.__value = ntuple._make(unpack(self.__size, buff))

    def _get(self):
        l = []
        for i in self.__value._fields:
            l.append(getattr(self.__value, i))
        return pack(self.__size, *l)

    def _export(self):
        return [x for x in self.__value._fields]

    def get_value_buff(self):
        return self._get()

    def get_value(self):
        return self.__value

    def set_value(self, attr):
        self.__value = self.__value._replace(**attr)

    def __str__(self):
        return self.__value.__str__()


def object_to_str(obj):
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, bool):
        return ""
    elif isinstance(obj, int):
        return pack("<L", obj)
    elif obj is None:
        return ""
    else:
        # print type(obj), obj
        return obj.get_raw()


class MethodBC(object):

    def show(self, value):
        getattr(self, "show_" + value)()


class BuffHandle(object):

    def __init__(self, buff):
        self.__buff = buff
        self.__idx = 0

    def size(self):
        return len(self.__buff)

    def set_idx(self, idx):
        self.__idx = idx

    def get_idx(self):
        return self.__idx

    def readNullString(self, size):
        data = self.read(size)
        return data

    def read_b(self, size):
        return self.__buff[self.__idx: self.__idx + size]

    def read_at(self, offset, size):
        return self.__buff[offset: offset + size]

    def read(self, size):
        if isinstance(size, SV):
            size = size.value

        buff = self.__buff[self.__idx: self.__idx + size]
        self.__idx += size

        return buff

    def end(self):
        return self.__idx == len(self.__buff)


class Buff(object):

    def __init__(self, offset, buff):
        self.offset = offset
        self.buff = buff

        self.size = len(buff)


class _Bytecode(object):

    def __init__(self, buff):
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

        self.__buff = buff
        self.__idx = 0

    def read(self, size):
        if isinstance(size, SV):
            size = size.value

        buff = self.__buff[self.__idx: self.__idx + size]
        self.__idx += size

        return buff

    def readat(self, off):
        if isinstance(off, SV):
            off = off.value

        return self.__buff[off:]

    def read_b(self, size):
        return self.__buff[self.__idx: self.__idx + size]

    def set_idx(self, idx):
        self.__idx = idx

    def get_idx(self):
        return self.__idx

    def add_idx(self, idx):
        self.__idx += idx

    def register(self, type_register, fct):
        self.__registers[type_register].append(fct)

    def get_buff(self):
        return self.__buff

    def length_buff(self):
        return len(self.__buff)

    def set_buff(self, buff):
        self.__buff = buff

    def save(self, filename):
        buff = self._save()
        with open(filename, "w") as fd:
            fd.write(buff)
