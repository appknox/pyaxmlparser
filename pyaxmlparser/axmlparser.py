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
import os
import logging
from struct import unpack
from collections import defaultdict
from zipfile import ZipFile, is_zipfile

import pyaxmlparser.constants as const
from pyaxmlparser import bytecode
from pyaxmlparser.stringblock import StringBlock
from pyaxmlparser import public
from . import arscutil
from pyaxmlparser.utils import string_types, text_type


class AXMLParser(object):
    def __init__(self, raw_buff=None, debug=False):
        self.log = logging.getLogger('pyaxmlparser.axmlparser')
        self.log.setLevel(logging.DEBUG if debug else logging.CRITICAL)
        self.event = -1
        self.line_number = -1
        self.name = -1
        self.namespace_uri = -1
        self.attributes = []
        self.id_attribute = -1
        self.class_attribute = -1
        self.style_attribute = -1
        self.namespace = -1
        data = b''

        if hasattr(raw_buff, 'read'):
            data = raw_buff.read()
        else:
            path_to_file = None
            try:
                if os.path.exists(raw_buff):
                    path_to_file = raw_buff
            except BaseException:
                pass
            if path_to_file:
                if is_zipfile(path_to_file):
                    with ZipFile(path_to_file, 'r') as apk:
                        if 'AndroidManifest.xml' in apk.namelist():
                            data = apk.read('AndroidManifest.xml')
                else:
                    with open(path_to_file, 'rb') as xml_file:
                        data = xml_file.read()
            else:
                data = raw_buff

        if not isinstance(data, string_types):
            raise ValueError('AXMLParser need file path to apk or xml, str or bytes data.')
        if isinstance(data, text_type):
            data = bytearray(data, encoding='utf-8')
        else:
            data = bytearray(data)

        self.valid_android_xml = True
        self.android_xml_tampered = False
        self.packer_warning = False
        self.buff = bytecode.BuffHandle(data)
        android_xml_file, = unpack('<L', self.buff.read(4))

        if android_xml_file != const.CHUNK_ANDROID_XML_FILE:
            # It looks like the header is wrong.
            # need some other checks.
            # We noted, that a some of files start with 0x0008NNNN,
            # where NNNN is some random number

            if android_xml_file >> 16 == 0x0008:
                self.android_xml_tampered = True
                self.log.warning(
                    'ANDROID XML file has an unusual header, most malware like '
                    'doing such stuff to anti androguard! But we try to parse '
                    'it anyways. Header: 0x{:08x}'.format(android_xml_file)
                )
            else:
                self.valid_android_xml = False
                self.log.warning('Not a valid ANDROID XML file. Header 0x{:08x}'.format(android_xml_file))
                return

        # Next is the filesize
        self.filesize, = unpack('<L', self.buff.read(4))
        assert self.filesize <= self.buff.size(), (
            'Declared filesize does not match real size: {} vs {}'.format(
                self.filesize, self.buff.size()
            )
        )

        # Now we parse the STRING POOL
        header = arscutil.ARSCHeader(self.buff)  # read 8 byte=header+chunk_size
        assert header.type == const.RES_STRING_POOL_TYPE, (
            'Expected String Pool header, got %x' % header.type
        )

        self.string_block = StringBlock(self.buff, header)

        self.resource_ids = []
        self.prefix_uri = {}
        self.uri_prefix = defaultdict(list)
        # Contains a list of current prefix/uri pairs
        self.prefix_uri_list = []
        # Store which namespaces are already printed
        self.visited_ns = []

    def is_valid(self):
        return self.valid_android_xml

    def reset(self):
        self.event = -1
        self.line_number = -1
        self.name = -1
        self.namespace_uri = -1
        self.attributes = []
        self.id_attribute = -1
        self.class_attribute = -1
        self.style_attribute = -1
        self.namespace = -1

    def next(self):
        return self.__next__()

    def __next__(self):
        self.do_next()
        return self.event

    def do_next(self):
        if self.event == const.END_DOCUMENT:
            return

        event = self.event

        self.reset()
        while True:
            # General notes:
            # * chunk_size is from start of chunk, including the tag type

            # Fake END_DOCUMENT event.
            if event == const.END_TAG:
                pass

            # START_DOCUMENT
            if event == const.START_DOCUMENT:
                chunk_type = const.CHUNK_XML_START_TAG
            else:
                # Stop at the declared filesize or at the end of the file
                if self.buff.end() or self.buff.get_idx() == self.filesize:
                    self.event = const.END_DOCUMENT
                    break
                chunk_type = unpack('<L', self.buff.read(4))[0]

            # Parse ResourceIDs. This chunk is after the String section
            if chunk_type == const.CHUNK_RESOURCE_IDS:
                chunk_size = unpack('<L', self.buff.read(4))[0]

                # Check size: < 8 bytes mean that the chunk is not complete
                # Should be aligned to 4 bytes.
                if chunk_size < 8 or chunk_size % 4 != 0:
                    self.log.warning('Invalid chunk size in chunk RESOURCEIDS')

                for i in range(0, (chunk_size // 4) - 2):
                    self.resource_ids.append(
                        unpack('<L', self.buff.read(4))[0])

                continue

            # FIXME, unknown chunk types might cause problems
            if chunk_type < const.CHUNK_XML_FIRST or \
                    chunk_type > const.CHUNK_XML_LAST:
                self.log.warning('invalid chunk type 0x{:08x}'.format(chunk_type))

            # Fake START_DOCUMENT event.
            if chunk_type == const.CHUNK_XML_START_TAG and event == -1:
                self.event = const.START_DOCUMENT
                break

            # After the chunk_type, there are always 3 fields for the remaining
            # tags we need to parse:
            # Chunk Size (we do not need it)
            # TODO for sanity checks, we should use it and check if the chunks
            # are correct in size
            self.buff.read(4)
            # Line Number
            self.line_number = unpack('<L', self.buff.read(4))[0]
            # Comment_Index (usually 0xFFFFFFFF, we do not need it)
            self.buff.read(4)

            # Now start to parse the field

            # There are five (maybe more) types of Chunks:
            # * START_NAMESPACE
            # * END_NAMESPACE
            # * START_TAG
            # * END_TAG
            # * TEXT
            if chunk_type == const.CHUNK_XML_START_NAMESPACE or \
                    chunk_type == const.CHUNK_XML_END_NAMESPACE:
                if chunk_type == const.CHUNK_XML_START_NAMESPACE:
                    prefix = unpack('<L', self.buff.read(4))[0]
                    uri = unpack('<L', self.buff.read(4))[0]

                    # FIXME We will get a problem here, if the same uri is used
                    # with different prefixes!
                    # prefix --> uri is a 1:1 mapping
                    self.prefix_uri[prefix] = uri
                    # but uri --> prefix is a 1:n mapping!
                    self.uri_prefix[uri].append(prefix)
                    self.prefix_uri_list.append((prefix, uri))
                    self.namespace = uri

                    # Workaround for closing tags
                    if (uri, prefix) in self.visited_ns:
                        self.visited_ns.remove((uri, prefix))
                else:
                    self.namespace = -1
                    # END_PREFIX contains again prefix and uri field
                    prefix, = unpack('<L', self.buff.read(4))
                    uri, = unpack('<L', self.buff.read(4))

                    # We can then remove those from the prefix_uri_list
                    if (prefix, uri) in self.prefix_uri_list:
                        self.prefix_uri_list.remove((prefix, uri))

                    # We also remove the entry from prefix_uri and uri_prefix:
                    if prefix in self.prefix_uri:
                        del self.prefix_uri[prefix]
                    if uri in self.uri_prefix:
                        self.uri_prefix[uri].remove(prefix)
                    # Need to remove them from visited namespaces as well, as it might pop up later
                    # FIXME we need to remove it also if we leave a tag which closes it namespace
                    # Workaround for now: remove it on a START_NAMESPACE tag
                    if (uri, prefix) in self.visited_ns:
                        self.visited_ns.remove((uri, prefix))

                    else:
                        self.log.warning(
                            'Reached a NAMESPACE_END without having the '
                            'namespace stored before? Prefix ID: {}, URI ID: '
                            '{}'.format(prefix, uri)
                        )

                continue

            # START_TAG is the start of a new tag.
            if chunk_type == const.CHUNK_XML_START_TAG:
                # The TAG consists of some fields:
                # * (chunk_size, line_number, comment_index - we read before)
                # * namespace_uri
                # * name
                # * flags
                # * attribute_count
                # * class_attribute
                # After that, there are two lists of attributes, 20 bytes each

                self.namespace_uri = unpack('<L', self.buff.read(4))[0]
                self.name = unpack('<L', self.buff.read(4))[0]

                # FIXME
                self.buff.read(4)  # flags

                attribute_count = unpack('<L', self.buff.read(4))[0]
                self.id_attribute = (attribute_count >> 16) - 1
                attribute_count = attribute_count & 0xFFFF
                self.class_attribute = unpack('<L', self.buff.read(4))[0]
                self.style_attribute = (self.class_attribute >> 16) - 1

                self.class_attribute = (self.class_attribute & 0xFFFF) - 1

                # Now, we parse the attributes.
                # Each attribute has 5 fields of 4 byte
                for i in range(0, attribute_count * const.ATTRIBUTE_LENGHT):
                    # Each field is linearly parsed into the array
                    self.attributes.append(unpack('<L', self.buff.read(4))[0])

                # Then there are class_attributes
                for i in range(const.ATTRIBUTE_IX_VALUE_TYPE, len(self.attributes),
                               const.ATTRIBUTE_LENGHT):
                    self.attributes[i] = self.attributes[i] >> 24

                self.event = const.START_TAG
                break

            if chunk_type == const.CHUNK_XML_END_TAG:
                self.namespace_uri = unpack('<L', self.buff.read(4))[0]
                self.name = unpack('<L', self.buff.read(4))[0]
                self.event = const.END_TAG
                break

            if chunk_type == const.CHUNK_XML_TEXT:
                # TODO we do not know what the TEXT field does...
                self.name = unpack('<L', self.buff.read(4))[0]

                # FIXME
                # Raw_value
                self.buff.read(4)
                # typed_value, is an enum
                self.buff.read(4)

                self.event = const.TEXT
                break

    def get_prefix_by_uri(self, uri):
        # As uri --> prefix is 1:n mapping,
        # We will just return the first one we match.
        if uri not in self.uri_prefix:
            return -1
        else:
            if len(self.uri_prefix[uri]) == 0:
                return -1
            return self.uri_prefix[uri][0]

    def get_prefix(self):
        # The default is, that the namespaceUri is 0xFFFFFFFF
        # Then we know, there is none
        if self.namespace_uri == 0xFFFFFFFF:
            return ''

        # FIXME this could be problematic. Need to find the correct namespace prefix
        if self.namespace_uri in self.uri_prefix:
            candidate = self.uri_prefix[self.namespace_uri][0]
            try:
                return self.string_block.get_string(candidate)
            except KeyError:
                return ''
        else:
            return ''

    def get_name(self):
        if self.name == -1 or (
                self.event != const.START_TAG and
                self.event != const.END_TAG):
            return ''

        return self.string_block.get_string(self.name)

    def get_text(self):
        if self.name == -1 or self.event != const.TEXT:
            return ''

        return self.string_block.get_string(self.name)

    def get_namespace_prefix(self, pos):
        prefix = self.prefix_uri_list[pos][0]
        return self.string_block.get_string(prefix)

    def get_namespace_uri(self, pos):
        uri = self.prefix_uri_list[pos][1]
        return self.string_block.get_string(uri)

    def get_xml_namespace(self):
        buff = ''
        for prefix, uri in self.prefix_uri.items():
            if (uri, prefix) not in self.visited_ns:
                prefix_str = self.string_block.get_string(prefix)
                prefix_uri = self.string_block.get_string(self.prefix_uri[prefix])
                # FIXME Packers like Liapp use empty uri to fool XML Parser
                # FIXME they also mess around with the Manifest, thus it can not be parsed easily
                if prefix_uri == '':
                    self.log.warning('Empty Namespace URI for Namespace {}.'.format(prefix_str))
                    self.packer_warning = True

                # if prefix is (null), which is indicated by an empty str, then do not print :
                if prefix_str != '':
                    prefix_str = ':' + prefix_str
                buff += 'xmlns{}="{}"\n'.format(prefix_str, prefix_uri)
                self.visited_ns.append((uri, prefix))
        return buff

    def get_namespace_count(self, pos):
        pass

    def get_attribute_offset(self, index):
        # FIXME
        if self.event != const.START_TAG:
            self.log.warning('Current event is not START_TAG.')

        offset = (index * 5) - 5
        # FIXME
        if offset >= len(self.attributes):
            self.log.warning('Invalid attribute index')

        return offset

    def get_attribute_count(self):
        return len(self.attributes) // const.ATTRIBUTE_LENGHT if self.event == const.START_TAG else -1

    def get_attribute_prefix(self, index):
        offset = self.get_attribute_offset(index)
        uri = self.attributes[offset + const.ATTRIBUTE_IX_NAMESPACE_URI]
        prefix = self.get_prefix_by_uri(uri)
        return self.string_block.get_string(prefix) if prefix != -1 else ''

    def get_attribute_name(self, index):
        offset = self.get_attribute_offset(index)
        name = self.attributes[offset + const.ATTRIBUTE_IX_NAME]

        if name == -1:
            return ''

        res = self.string_block.get_string(name)
        # If the result is a (null) string, we need to look it up.
        if not res:
            attr = self.resource_ids[name]
            if attr in public.SYSTEM_RESOURCES['attributes']['inverse']:
                res = 'android:' + public.SYSTEM_RESOURCES['attributes']['inverse'][
                    attr
                ]
            else:
                # Attach the HEX Number, so for multiple missing attributes we do not run
                # into problems.
                res = 'android:UNKNOWN_SYSTEM_ATTRIBUTE_{:08x}'.format(attr)

        return res

    def get_attribute_value_type(self, index):
        offset = self.get_attribute_offset(index)
        return self.attributes[offset + const.ATTRIBUTE_IX_VALUE_TYPE]

    def get_attribute_value_data(self, index):
        offset = self.get_attribute_offset(index)
        return self.attributes[offset + const.ATTRIBUTE_IX_VALUE_DATA]

    def get_attribute_value(self, index):
        """
        This function is only used to look up strings
        All other work is made by format_value
        # FIXME should unite those functions
        :param index:
        :return:
        """
        offset = self.get_attribute_offset(index)
        value_type = self.attributes[offset + const.ATTRIBUTE_IX_VALUE_TYPE]
        if value_type == const.TYPE_STRING:
            value_string = self.attributes[offset + const.ATTRIBUTE_IX_VALUE_STRING]
            return self.string_block.get_string(value_string)
        return ''
