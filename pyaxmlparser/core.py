from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.utils import get_zip_file


class APK:
    def __init__(self, resource):
        self.resource = resource
        self.zip_file = get_zip_file(resource)

    def validate(self):
        files = set(self.zip_file.namelist())
        required_files = {'AndroidManifest.xml', 'resources.arsc'}
        assert required_files.issubset(files)

    @property
    def package_name(self):
        axml_file = self.zip_file.read('AndroidManifest.xml')
        axml = AXMLPrinter(axml_file).get_xml_obj()
        app_name_hex = axml.getElementsByTagName("application")[0].getAttribute("android:label")
        appnamehex = '0x' + app_name_hex[1:]

        rsc_file = self.zip_file.read('resources.arsc')
        rsc = ARSCParser(rsc_file)

        app_name = rsc.get_string(
            rsc.get_packages_names()[0],
            rsc.get_id(rsc.get_packages_names()[0], int(appnamehex, 0))[1]
        )
        return app_name[1]
