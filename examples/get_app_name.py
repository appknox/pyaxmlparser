"""
Usage:
python get_app_name.py /path/to/extracted/apk/dir
"""
import os
import sys
from pyaxmlparser import ARSCParser, AXMLPrinter
from pyaxmlparser.utils import NS_ANDROID

app_root = sys.argv[1]
axml_file = os.path.join(app_root, 'AndroidManifest.xml')
rsc_file = os.path.join(app_root, 'resources.arsc')

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
    print('App name is \'{}\''.format(app_name[1]))
