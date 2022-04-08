import os.path
import sys
import unittest

from lxml import etree

from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlparser import AXMLParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.utils import NS_ANDROID


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
