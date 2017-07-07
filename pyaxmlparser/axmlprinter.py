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

from pyaxmlparser.axmlparser import AXMLParser
from pyaxmlparser.utils import parse_lxml_dom
from struct import pack, unpack
from lxml import etree
from xml.sax.saxutils import escape
from pyaxmlparser.utils import _range
import pyaxmlparser.constants as const


def complexToFloat(xcomplex):
    return \
        (float)(xcomplex & 0xFFFFFF00) * const.RADIX_MULTS[(xcomplex >> 4) & 3]


class AXMLPrinter(object):

    def __init__(self, raw_buff):
        self.axml = AXMLParser(raw_buff)
        self.xmlns = False

        self.buff = ''

        while True and self.axml.is_valid():
            _type = next(self.axml)
#           print "tagtype = ", _type

            if _type == const.START_DOCUMENT:
                self.buff += '<?xml version="1.0" encoding="utf-8"?>\n'
            elif _type == const.START_TAG:
                self.buff += '<' + \
                    self.getPrefix(self.axml.getPrefix()) + \
                    self.axml.getName() + '\n'
                self.buff += self.axml.getXMLNS()

                for i in _range(0, self.axml.getAttributeCount()):
                    self.buff += "%s%s=\"%s\"\n" % (
                        self.getPrefix(self.axml.getAttributePrefix(i)),
                        self.axml.getAttributeName(i),
                        self._escape(self.getAttributeValue(i)))

                self.buff += '>\n'

            elif _type == const.END_TAG:
                self.buff += "</%s%s>\n" % (self.getPrefix(
                    self.axml.getPrefix()), self.axml.getName())

            elif _type == const.TEXT:
                self.buff += "%s\n" % self.axml.getText()

            elif _type == const.END_DOCUMENT:
                break

    # pleed patch
    def _escape(self, s):
        s = s.replace("&", "&amp;")
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        return escape(s)

    def get_buff(self):
        return self.buff

    def get_xml(self):
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(self.get_buff().encode(), parser=parser)
        return parse_lxml_dom(tree).toprettyxml(encoding="utf-8")
        # return minidom.parseString(self.get_buff()).toprettyxml(
        #   encoding="utf-8")

    def get_xml_obj(self):
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(self.get_buff().encode(), parser=parser)
        return parse_lxml_dom(tree)
        # return minidom.parseString(self.get_buff())

    def getPrefix(self, prefix):
        if prefix is None or len(prefix) == 0:
            return ''

        return prefix + ':'

    def getAttributeValue(self, index):
        _type = self.axml.getAttributeValueType(index)
        _data = self.axml.getAttributeValueData(index)

        if _type == const.TYPE_STRING:
            return self.axml.getAttributeValue(index)

        elif _type == const.TYPE_ATTRIBUTE:
            return "?%s%08X" % (self.getPackage(_data), _data)

        elif _type == const.TYPE_REFERENCE:
            return "@%s%08X" % (self.getPackage(_data), _data)

        elif _type == const.TYPE_FLOAT:
            return "%f" % unpack("=f", pack("=L", _data))[0]

        elif _type == const.TYPE_INT_HEX:
            return "0x%08X" % _data

        elif _type == const.TYPE_INT_BOOLEAN:
            if _data == 0:
                return "false"
            return "true"

        elif _type == const.TYPE_DIMENSION:
            return "%f%s" % (
                complexToFloat(_data),
                const.DIMENSION_UNITS[_data & const.COMPLEX_UNIT_MASK])

        elif _type == const.TYPE_FRACTION:
            return "%f%s" % (
                complexToFloat(_data) * 100,
                const.FRACTION_UNITS[_data & const.COMPLEX_UNIT_MASK])

        elif _type >= const.TYPE_FIRST_COLOR_INT \
                and _type <= const.TYPE_LAST_COLOR_INT:
            return "#%08X" % _data

        elif _type >= const.TYPE_FIRST_INT and _type <= const.TYPE_LAST_INT:
            return "%d" % _data

        return "<0x%X, type 0x%02X>" % (_data, _type)

    def getPackage(self, id):
        if id >> 24 == 1:
            return "android:"
        return ""
