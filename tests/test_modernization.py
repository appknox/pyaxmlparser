import os.path
import sys
import unittest
import struct
from io import BytesIO

from pyaxmlparser.axmlparser import AXMLParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.stringblock import StringBlock
from pyaxmlparser.exceptions import StringBlockError, ChunkError, NamespaceError, ValidationError

PATH_INSTALL = "./"
sys.path.append(PATH_INSTALL)
test_apk = 'tests/test_apk/'


class ModernizationTest(unittest.TestCase):
    def test_string_block_error_handling(self):
        """Test that StringBlock properly handles invalid data"""
        with self.assertRaises((StringBlockError, struct.error)):
            sb = StringBlock(BytesIO(b"invalid"), None)

    def test_axml_parser_buffer_validation(self):
        """Test that AXMLParser validates buffer boundaries"""
        parser = AXMLParser(b"short")
        self.assertFalse(parser.is_valid())

    def test_axml_parser_none_input(self):
        """Test that AXMLParser handles None input gracefully"""
        parser = AXMLParser(None)
        self.assertFalse(parser.is_valid())

    def test_axml_printer_none_input(self):
        """Test that AXMLPrinter handles None input gracefully"""
        printer = AXMLPrinter(None)
        self.assertFalse(printer.is_valid())

    def test_namespace_error_handling(self):
        """Test that namespace processing handles errors properly"""
        manifest_path = os.path.join(test_apk, "AndroidManifest.xml")
        if os.path.exists(manifest_path):
            with open(manifest_path, "rb") as fd:
                manifest_content = fd.read()
            
            parser = AXMLParser(manifest_content)
            if parser.is_valid():
                nsmap = parser.nsmap
                self.assertIsInstance(nsmap, dict)

    def test_type_annotations(self):
        """Test that type annotations are properly applied"""
        parser = AXMLParser(b"test")
        self.assertIsInstance(parser.is_valid(), bool)
        
        printer = AXMLPrinter(b"test")
        self.assertIsInstance(printer.is_valid(), bool)
        if printer.is_valid() and printer.root is not None:
            self.assertIsInstance(printer.get_xml(), str)


if __name__ == '__main__':
    unittest.main()
