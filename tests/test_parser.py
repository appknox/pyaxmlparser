import os.path
import sys

from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.utils import NS_ANDROID


PATH_INSTALL = "./"
sys.path.append(PATH_INSTALL)
test_apk = "tests/test_apk/"


def test_app_name_extraction():
    axml_file = os.path.join(test_apk, "AndroidManifest.xml")
    axml = AXMLPrinter(open(axml_file, "rb").read()).xml_object
    app_name_hex = axml.findall(".//application")[0].get(NS_ANDROID + "label")
    appnamehex = "0x" + app_name_hex[1:]

    rsc_file = os.path.join(test_apk, "resources.arsc")
    rsc = ARSCParser(open(rsc_file, "rb").read())

    app_name = rsc.get_string(
        rsc.first_package_name,
        rsc.get_id(rsc.first_package_name, int(appnamehex, 0))[1],
    )
    assert app_name == ["app_name", "Evie"]
