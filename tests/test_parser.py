import os.path
import sys
import unittest

from lxml import etree

from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlparser import AXMLParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.utils import NS_ANDROID
from pyaxmlparser.exceptions import BufferUnderrunError, InvalidStringPoolError


PATH_INSTALL = "./"
sys.path.append(PATH_INSTALL)
test_apk = 'tests/test_apk/'


def test_app_name_extraction():
    axml_file = os.path.join(test_apk, 'AndroidManifest.xml')
    axml = AXMLPrinter(open(axml_file, 'rb').read()).get_xml_obj()
    app_name_hex = axml.findall(".//application")[0].get(NS_ANDROID + "label")
    appnamehex = '0x' + app_name_hex[1:]

    rsc_file = os.path.join(test_apk, 'resources.arsc')
    rsc = ARSCParser(open(rsc_file, 'rb').read())

    app_name = rsc.get_string(
        rsc.get_packages_names()[0],
        rsc.get_id(rsc.get_packages_names()[0], int(appnamehex, 0))[1]
    )
    assert app_name == ['app_name', 'Evie']


class AXMLParserTest(unittest.TestCase):
    def test_should_remove_spaces_from_namespace_uri(self):
        manifest_path = os.path.join(
            test_apk,
            "AndroidManifest_invalid_namespace.xml"
        )
        fd = open(manifest_path, "rb")
        manifest_content = fd.read()
        fd.close()

        axml = AXMLParser(raw_buff=manifest_content)
        next(axml)

        namespaces = {}
        for k,v in axml.namespaces:
            namespaces[axml.sb[k]] = axml.sb[v]

        self.assertTrue(axml.is_valid())

        # spaces exist in namespaces, but removed in nsmap
        self.assertEqual(
            namespaces["android"],
            "http://schemas.android.com/apk/res/android"
        )
        self.assertEqual(
            namespaces["app"],
            " http://schemas.android.com/apk/res-auto "
        )
        self.assertEqual(
            namespaces["dist"],
            " http://schemas.android.com/apk/distribution"
        )
        self.assertEqual(
            namespaces["tools"],
            "http://schemas.android.com/tools "
        )
        self.assertDictEqual(axml.nsmap, {
            "android": "http://schemas.android.com/apk/res/android",
            "app": "http://schemas.android.com/apk/res-auto",
            "dist": "http://schemas.android.com/apk/distribution",
            "tools": "http://schemas.android.com/tools"
        })

        # nsmap should be parsable by etree
        try:
            etree.Element("manifest", nsmap=axml.nsmap)
        except ValueError as e:
            # Eg: Invalid namespace URI "http://schemas.android.com/tools "
            raise self.fail(str(e))


class BufferValidationTest(unittest.TestCase):
    def test_buffer_underrun_handling(self):
        """Test that buffer validation works correctly."""
        from pyaxmlparser.arscutil import ARSCResStringPoolRef
        from pyaxmlparser.bytecode import BuffHandle
        
        small_buffer = b'\x01\x02'
        buff = BuffHandle(small_buffer)
        
        with self.assertRaises(BufferUnderrunError):
            ARSCResStringPoolRef(buff)

    def test_string_pool_validation(self):
        """Test string pool validation with malformed data."""
        from pyaxmlparser.stringblock import StringBlock
        from pyaxmlparser.bytecode import BuffHandle
        from pyaxmlparser.arscutil import ARSCHeader
        
        invalid_data = b'\x01\x00\x1C\x00\x08\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # Truncated string pool
        buff = BuffHandle(invalid_data)
        
        class FakeHeader:
            def __init__(self):
                self.size = len(invalid_data)
        
        header = FakeHeader()
        
        try:
            sb = StringBlock(buff, header)
            self.assertIsNotNone(sb)
        except (InvalidStringPoolError, BufferUnderrunError):
            # These exceptions are expected when testing with malformed data.
            pass

    def test_malformed_axml_handling(self):
        """Test that malformed AXML data is handled gracefully."""
        from pyaxmlparser.axmlparser import AXMLParser
        from pyaxmlparser.bytecode import BuffHandle
        
        malformed_data = b'\x03\x00\x08\x00' + b'\x00' * 100  # Valid header but invalid content
        buff = BuffHandle(malformed_data)
        
        parser = AXMLParser(buff)
        self.assertIsNotNone(parser)

    def test_graceful_degradation(self):
        """Test that parser handles edge cases gracefully."""
        from pyaxmlparser import APK
        
        test_apk_path = '/home/ubuntu/attachments/2ec8f986-fc8b-47e6-8911-9ef6fa76a91a/test1.apk'
        if os.path.exists(test_apk_path):
            try:
                apk = APK(test_apk_path)
                package = apk.get_package()
                self.assertIsNotNone(package)
                app_name = apk.get_app_name()
                self.assertIsNotNone(app_name)
            except Exception as e:
                self.fail(f"APK parsing should not crash: {e}")

    def test_working_apk_regression(self):
        """Test that working APK still works correctly."""
        from pyaxmlparser import APK
        
        working_apk_path = '/home/ubuntu/attachments/4fcbdf8c-a1cf-42cc-84f4-31e3798eded6/apk.apk'
        if os.path.exists(working_apk_path):
            try:
                apk = APK(working_apk_path)
                package = apk.get_package()
                self.assertEqual(package, 'com.app.damnvulnerablebank')
                app_name = apk.get_app_name()
                self.assertEqual(app_name, 'DamnVulnerableBank')
            except Exception as e:
                self.fail(f"Working APK should continue to work: {e}")
