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
from pyaxmlparser.utils import format_value
import pyaxmlparser.constants as const
from xml.sax.saxutils import escape
from lxml import etree


class AXMLPrinter(object):
    """
    Converter for AXML Files into a XML string
    """
    def __init__(self, raw_buff):
        self.axml = AXMLParser(raw_buff)
        self.xmlns = False

        self.buff = u''

        while True and self.axml.is_valid():
            _type = next(self.axml)

            if _type == const.START_DOCUMENT:
                self.buff += u'<?xml version="1.0" encoding="utf-8"?>\n'
            elif _type == const.START_TAG:
                self.buff += u'<' + self.getPrefix(self.axml.getPrefix()) + \
                    self.axml.getName() + u'\n'
                self.buff += self.axml.getXMLNS()

                for i in range(0, self.axml.getAttributeCount()):
                    prefix = self.getPrefix(self.axml.getAttributePrefix(i))
                    name = self.axml.getAttributeName(i)
                    value = self._escape(self.getAttributeValue(i))

                    # If the name is a system name AND the prefix is set,
                    # we have a problem.
                    # FIXME we are not sure how this happens, but a quick fix
                    # is to remove the prefix if it already in the name
                    if name.startswith(prefix):
                        prefix = u''

                    self.buff += u'{}{}="{}"\n'.format(prefix, name, value)

                self.buff += u'>\n'

            elif _type == const.END_TAG:
                self.buff += u"</%s%s>\n" % (
                    self.getPrefix(self.axml.getPrefix()), self.axml.getName())

            elif _type == const.TEXT:
                self.buff += u"%s\n" % self._escape(self.axml.getText())
            elif _type == const.END_DOCUMENT:
                break

    # pleed patch
    # FIXME should this be applied for strings directly?
    def _escape(self, s):
        # FIXME Strings might contain null bytes. Should they be removed?
        # We guess so, as normaly the string would terminate there...?!
        s = s.replace("\x00", "")
        # Other HTML Conversions
        s = s.replace("&", "&amp;")
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        return escape(s)

    def is_packed(self):
        """
        Return True if we believe that the AXML file is packed
        If it is, we can not be sure that the AXML file can be read by a XML
        Parser
        :return: boolean
        """
        return self.axml.packerwarning

    def get_buff(self):
        return self.buff.encode('utf-8')

    def get_xml(self):
        """
        Get the XML as an UTF-8 string
        :return: str
        """
        return etree.tostring(
            self.get_xml_obj(), encoding="utf-8", pretty_print=True)

    def get_xml_obj(self):
        """
        Get the XML as an ElementTree object
        :return: :class:`~lxml.etree.Element`
        """
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        tree = etree.fromstring(self.get_buff(), parser=parser)
        return tree

    def getPrefix(self, prefix):
        if prefix is None or len(prefix) == 0:
            return u''

        return prefix + u':'

    def getAttributeValue(self, index):
        """
        Wrapper function for format_value
        to resolve the actual value of an attribute in a tag
        :param index:
        :return:
        """
        _type = self.axml.getAttributeValueType(index)
        _data = self.axml.getAttributeValueData(index)

        return format_value(
            _type, _data, lambda _: self.axml.getAttributeValue(index))
