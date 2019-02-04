"""
Usage:
python get_app_name.py /path/to/extracted/apk/dir
"""
import sys

from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter


app_root = sys.argv[1]

xml = AXMLPrinter(open("{}/AndroidManifest.xml".format(app_root), 'rb').read()).get_xml_obj()
rsc = ARSCParser(open("{}/resources.arsc".format(app_root), "rb").read())

app_name_hex = xml.getElementsByTagName("application")[0].getAttribute("android:label")
app_name = '0x' + app_name_hex[1:]
app_name = rsc.get_string(
    rsc.get_packages_names()[0],
    rsc.get_id(rsc.get_packages_names()[0], int(app_name, 0))[1]
)
print('App name is "{}"'.format(app_name[1]))
