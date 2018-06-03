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
from collections import defaultdict

import pyaxmlparser.constants as const
from pyaxmlparser import bytecode
from pyaxmlparser.stringblock import StringBlock
from pyaxmlparser import public
from . import arscutil


class AXMLParser(object):
    def __init__(self, raw_buff):
        self.reset()

        self.valid_axml = True
        self.axml_tampered = False
        self.packerwarning = False
        self.buff = bytecode.BuffHandle(raw_buff)

        axml_file, = unpack('<L', self.buff.read(4))

        if axml_file != const.CHUNK_AXML_FILE:
            # It looks like the header is wrong.
            # need some other checks.
            # We noted, that a some of files start with 0x0008NNNN,
            # where NNNN is some random number

            if axml_file >> 16 == 0x0008:
                self.axml_tampered = True
                warn(
                    "AXML file has an unusual header, most malwares like "
                    "doing such stuff to anti androguard! But we try to parse "
                    "it anyways. Header: 0x{:08x}".format(axml_file)
                )
            else:
                self.valid_axml = False
                warn("Not a valid AXML file. Header 0x{:08x}".format(axml_file))
                return

        # Next is the filesize
        self.filesize, = unpack('<L', self.buff.read(4))
        assert self.filesize <= self.buff.size(), (
            "Declared filesize does not match real size: {} vs {}".format(
                self.filesize, self.buff.size()
            )
        )

        # Now we parse the STRING POOL
        header = arscutil.ARSCHeader(self.buff)  # read 8 byte=header+chunk_size
        assert header.type == const.RES_STRING_POOL_TYPE, (
            "Expected String Pool header, got %x" % header.type
        )

        self.sb = StringBlock(self.buff, header)

        self.m_resourceIDs = []
        self.m_prefixuri = {}
        self.m_uriprefix = defaultdict(list)
        # Contains a list of current prefix/uri pairs
        self.m_prefixuriL = []
        # Store which namespaces are already printed
        self.visited_ns = []

    def is_valid(self):
        return self.valid_axml

    def reset(self):
        self.m_event = -1
        self.m_lineNumber = -1
        self.m_name = -1
        self.m_namespaceUri = -1
        self.m_attributes = []
        self.m_idAttribute = -1
        self.m_classAttribute = -1
        self.m_styleAttribute = -1

    def __next__(self):
        self.doNext()
        return self.m_event

    def doNext(self):
        if self.m_event == const.END_DOCUMENT:
            return

        event = self.m_event

        self.reset()
        while True:
            chunkType = -1
            # General notes:
            # * chunkSize is from start of chunk, including the tag type

            # Fake END_DOCUMENT event.
            if event == const.END_TAG:
                pass

            # START_DOCUMENT
            if event == const.START_DOCUMENT:
                chunkType = const.CHUNK_XML_START_TAG
            else:
                # Stop at the declared filesize or at the end of the file
                if self.buff.end() or self.buff.get_idx() == self.filesize:
                    self.m_event = const.END_DOCUMENT
                    break
                chunkType = unpack('<L', self.buff.read(4))[0]

            # Parse ResourceIDs. This chunk is after the String section
            if chunkType == const.CHUNK_RESOURCEIDS:
                chunkSize = unpack('<L', self.buff.read(4))[0]

                # Check size: < 8 bytes mean that the chunk is not complete
                # Should be aligned to 4 bytes.
                if chunkSize < 8 or chunkSize % 4 != 0:
                    warn("Invalid chunk size in chunk RESOURCEIDS")

                for i in range(0, (chunkSize // 4) - 2):
                    self.m_resourceIDs.append(
                        unpack('<L', self.buff.read(4))[0])

                continue

            # FIXME, unknown chunk types might cause problems
            if chunkType < const.CHUNK_XML_FIRST or \
                    chunkType > const.CHUNK_XML_LAST:
                warn("invalid chunk type 0x{:08x}".format(chunkType))

            # Fake START_DOCUMENT event.
            if chunkType == const.CHUNK_XML_START_TAG and event == -1:
                self.m_event = const.START_DOCUMENT
                break

            # After the chunk_type, there are always 3 fields for the remaining
            # tags we need to parse:
            # Chunk Size (we do not need it)
            # TODO for sanity checks, we should use it and check if the chunks
            # are correct in size
            self.buff.read(4)
            # Line Number
            self.m_lineNumber = unpack('<L', self.buff.read(4))[0]
            # Comment_Index (usually 0xFFFFFFFF, we do not need it)
            self.buff.read(4)

            # Now start to parse the field

            # There are five (maybe more) types of Chunks:
            # * START_NAMESPACE
            # * END_NAMESPACE
            # * START_TAG
            # * END_TAG
            # * TEXT
            if chunkType == const.CHUNK_XML_START_NAMESPACE or \
                    chunkType == const.CHUNK_XML_END_NAMESPACE:
                if chunkType == const.CHUNK_XML_START_NAMESPACE:
                    prefix = unpack('<L', self.buff.read(4))[0]
                    uri = unpack('<L', self.buff.read(4))[0]

                    # FIXME We will get a problem here, if the same uri is used
                    # with different prefixes!
                    # prefix --> uri is a 1:1 mapping
                    self.m_prefixuri[prefix] = uri
                    # but uri --> prefix is a 1:n mapping!
                    self.m_uriprefix[uri].append(prefix)
                    self.m_prefixuriL.append((prefix, uri))
                    self.ns = uri

                    # Workaround for closing tags
                    if (uri, prefix) in self.visited_ns:
                        self.visited_ns.remove((uri, prefix))
                else:
                    self.ns = -1
                    # END_PREFIX contains again prefix and uri field
                    prefix, = unpack('<L', self.buff.read(4))
                    uri, = unpack('<L', self.buff.read(4))

                    # We can then remove those from the prefixuriL
                    if (prefix, uri) in self.m_prefixuriL:
                        self.m_prefixuriL.remove((prefix, uri))

                    # We also remove the entry from prefixuri and uriprefix:
                    if prefix in self.m_prefixuri:
                        del self.m_prefixuri[prefix]
                    if uri in self.m_uriprefix:
                        self.m_uriprefix[uri].remove(prefix)
                    # Need to remove them from visisted namespaces as well, as it might pop up later
                    # FIXME we need to remove it also if we leave a tag which closes it namespace
                    # Workaround for now: remove it on a START_NAMESPACE tag
                    if (uri, prefix) in self.visited_ns:
                        self.visited_ns.remove((uri, prefix))

                    else:
                        warn(
                            "Reached a NAMESPACE_END without having the "
                            "namespace stored before? Prefix ID: {}, URI ID: "
                            "{}".format(prefix, uri)
                        )

                continue

            # START_TAG is the start of a new tag.
            if chunkType == const.CHUNK_XML_START_TAG:
                # The TAG consists of some fields:
                # * (chunk_size, line_number, comment_index - we read before)
                # * namespace_uri
                # * name
                # * flags
                # * attribute_count
                # * class_attribute
                # After that, there are two lists of attributes, 20 bytes each

                self.m_namespaceUri = unpack('<L', self.buff.read(4))[0]
                self.m_name = unpack('<L', self.buff.read(4))[0]

                # FIXME
                self.buff.read(4)  # flags

                attributeCount = unpack('<L', self.buff.read(4))[0]
                self.m_idAttribute = (attributeCount >> 16) - 1
                attributeCount = attributeCount & 0xFFFF
                self.m_classAttribute = unpack('<L', self.buff.read(4))[0]
                self.m_styleAttribute = (self.m_classAttribute >> 16) - 1

                self.m_classAttribute = (self.m_classAttribute & 0xFFFF) - 1

                # Now, we parse the attributes.
                # Each attribute has 5 fields of 4 byte
                for i in range(0, attributeCount * const.ATTRIBUTE_LENGHT):
                    # Each field is linearly parsed into the array
                    self.m_attributes.append(unpack('<L', self.buff.read(4))[0])

                # Then there are class_attributes
                for i in range(const.ATTRIBUTE_IX_VALUE_TYPE, len(self.m_attributes),
                               const.ATTRIBUTE_LENGHT):
                    self.m_attributes[i] = self.m_attributes[i] >> 24

                self.m_event = const.START_TAG
                break

            if chunkType == const.CHUNK_XML_END_TAG:
                self.m_namespaceUri = unpack('<L', self.buff.read(4))[0]
                self.m_name = unpack('<L', self.buff.read(4))[0]
                self.m_event = const.END_TAG
                break

            if chunkType == const.CHUNK_XML_TEXT:
                # TODO we do not know what the TEXT field does...
                self.m_name = unpack('<L', self.buff.read(4))[0]

                # FIXME
                # Raw_value
                self.buff.read(4)
                # typed_value, is an enum
                self.buff.read(4)

                self.m_event = const.TEXT
                break

    def getPrefixByUri(self, uri):
        # As uri --> prefix is 1:n mapping,
        # We will just return the first one we match.
        if uri not in self.m_uriprefix:
            return -1
        else:
            if len(self.m_uriprefix[uri]) == 0:
                return -1
            return self.m_uriprefix[uri][0]

    def getPrefix(self):
        # The default is, that the namespaceUri is 0xFFFFFFFF
        # Then we know, there is none
        if self.m_namespaceUri == 0xFFFFFFFF:
            return u''

        # FIXME this could be problematic. Need to find the correct namespace prefix
        if self.m_namespaceUri in self.m_uriprefix:
            candidate = self.m_uriprefix[self.m_namespaceUri][0]
            try:
                return self.sb.getString(candidate)
            except KeyError:
                return u''
        else:
            return u''

    def getName(self):
        if self.m_name == -1 or (
                self.m_event != const.START_TAG and
                self.m_event != const.END_TAG):
            return u''

        return self.sb.getString(self.m_name)

    def getText(self):
        if self.m_name == -1 or self.m_event != const.TEXT:
            return u''

        return self.sb.getString(self.m_name)

    def getNamespacePrefix(self, pos):
        prefix = self.m_prefixuriL[pos][0]
        return self.sb.getString(prefix)

    def getNamespaceUri(self, pos):
        uri = self.m_prefixuriL[pos][1]
        return self.sb.getString(uri)

    def getXMLNS(self):
        buff = ""
        for prefix, uri in self.m_prefixuri.items():
            if (uri, prefix) not in self.visited_ns:
                prefix_str = self.sb.getString(prefix)
                prefix_uri = self.sb.getString(self.m_prefixuri[prefix])
                # FIXME Packers like Liapp use empty uri to fool XML Parser
                # FIXME they also mess around with the Manifest, thus it can not be parsed easily
                if prefix_uri == '':
                    warn("Empty Namespace URI for Namespace {}.".format(prefix_str))
                    self.packerwarning = True

                # if prefix is (null), which is indicated by an empty str, then do not print :
                if prefix_str != '':
                    prefix_str = ":" + prefix_str
                buff += 'xmlns{}="{}"\n'.format(prefix_str, prefix_uri)
                self.visited_ns.append((uri, prefix))
        return buff

    def getNamespaceCount(self, pos):
        pass

    def getAttributeOffset(self, index):
        # FIXME
        if self.m_event != const.START_TAG:
            warn("Current event is not START_TAG.")

        offset = index * 5
        # FIXME
        if offset >= len(self.m_attributes):
            warn("Invalid attribute index")

        return offset

    def getAttributeCount(self):
        if self.m_event != const.START_TAG:
            return -1

        return len(self.m_attributes) // const.ATTRIBUTE_LENGHT

    def getAttributePrefix(self, index):
        offset = self.getAttributeOffset(index)
        uri = self.m_attributes[offset + const.ATTRIBUTE_IX_NAMESPACE_URI]

        prefix = self.getPrefixByUri(uri)

        if prefix == -1:
            return ""

        return self.sb.getString(prefix)

    def getAttributeName(self, index):
        offset = self.getAttributeOffset(index)
        name = self.m_attributes[offset + const.ATTRIBUTE_IX_NAME]

        if name == -1:
            return ""

        res = self.sb.getString(name)
        # If the result is a (null) string, we need to look it up.
        if not res:
            attr = self.m_resourceIDs[name]
            if attr in public.SYSTEM_RESOURCES['attributes']['inverse']:
                res = 'android:' + public.SYSTEM_RESOURCES['attributes']['inverse'][
                    attr
                ]
            else:
                # Attach the HEX Number, so for multiple missing attributes we do not run
                # into problems.
                res = 'android:UNKNOWN_SYSTEM_ATTRIBUTE_{:08x}'.format(attr)

        return res

    def getAttributeValueType(self, index):
        offset = self.getAttributeOffset(index)
        return self.m_attributes[offset + const.ATTRIBUTE_IX_VALUE_TYPE]

    def getAttributeValueData(self, index):
        offset = self.getAttributeOffset(index)
        return self.m_attributes[offset + const.ATTRIBUTE_IX_VALUE_DATA]

    def getAttributeValue(self, index):
        """
        This function is only used to look up strings
        All other work is made by format_value
        # FIXME should unite those functions
        :param index:
        :return:
        """
        offset = self.getAttributeOffset(index)
        valueType = self.m_attributes[offset + const.ATTRIBUTE_IX_VALUE_TYPE]
        if valueType == const.TYPE_STRING:
            valueString = self.m_attributes[offset + const.ATTRIBUTE_IX_VALUE_STRING]
            return self.sb.getString(valueString)
        return ""
