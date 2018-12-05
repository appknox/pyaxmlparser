from os import path

from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.utils import NS_ANDROID


def test_app_name_extraction():
    here = path.abspath(path.dirname(__file__))
    axml_file = path.join(here, 'tests/test_apk/AndroidManifest.xml')
    rsc_file = path.join(here, 'tests/test_apk/resources.arsc')
    with open(axml_file, 'rb') as manifest_file, open(rsc_file, 'rb') as resources_file:
        manifest_data = manifest_file.read()
        resources_data = resources_file.read()
        axml = AXMLPrinter(manifest_data).get_xml_obj()
        rsc = ARSCParser(resources_data)

        app_name_label = axml.findall('.//application')[0].get(NS_ANDROID + 'label')
        app_name_hex = '0x' + app_name_label[1:]

        app_name = rsc.get_string(
            rsc.get_packages_names()[0],
            rsc.get_id(rsc.get_packages_names()[0], int(app_name_hex, 0))[1]
        )
    assert app_name == ['app_name', 'Evie']
