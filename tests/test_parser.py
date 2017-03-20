import os.path
import sys

from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter


PATH_INSTALL = "./"
sys.path.append(PATH_INSTALL)
test_apk = 'tests/test_apk/'


def test_app_name_extraction():
    axml_file = os.path.join(test_apk, 'AndroidManifest.xml')
    axml = AXMLPrinter(open(axml_file, 'rb').read()).get_xml_obj()
    app_name_hex = axml.getElementsByTagName("application")[0].getAttribute("android:label")
    appnamehex = '0x' + app_name_hex[1:]

    rsc_file = os.path.join(test_apk, 'resources.arsc')
    rsc = ARSCParser(open(rsc_file, 'rb').read())

    app_name = rsc.get_string(
        rsc.get_packages_names()[0],
        rsc.get_id(rsc.get_packages_names()[0], int(appnamehex, 0))[1]
    )
    assert app_name == ['app_name', 'Evie']
