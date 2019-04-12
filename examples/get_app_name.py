"""
Usage:
python get_app_name.py /path/to/extracted/apk/dir
"""
import sys
import os

from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter

if len(sys.argv) < 2:
    print("Usage:\npython get_app_name.py /path/to/extracted/apk/dir")
    exit(1)

xml = None
rsc = None
app_name = None
manifest_path = os.path.join(sys.argv[1], "AndroidManifest.xml")
if os.path.exists(manifest_path):
    with open(manifest_path, "rb") as manifest_file:
        xml = AXMLPrinter(manifest_file.read()).xml_object

resources_path = os.path.join(sys.argv[1], "resources.arsc")
if os.path.exists(resources_path):
    with open(resources_path, "rb") as resources_file:
        rsc = ARSCParser(resources_file.read())
if xml and rsc:
    attribute = "android:label"
    attribute_ns = "{{http://schemas.android.com/apk/res/android}}android:label"
    app_name_hex = None
    for element_item in xml.findall(".//application"):
        value = None
        if element_item.get(attribute) is not None:
            value = element_item.get(attribute)
        elif element_item.get(attribute_ns) is not None:
            value = element_item.get(attribute_ns)
        if value is not None:
            app_name_hex = value
            break
    if app_name_hex:
        app_name = "0x" + app_name_hex[1:]
        app_name = rsc.get_string(
            rsc.first_package_name,
            rsc.get_id(rsc.first_package_name, int(app_name, 0))[1],
        )[1]
print('App name is "{}"'.format(app_name if app_name else "Unknown"))
