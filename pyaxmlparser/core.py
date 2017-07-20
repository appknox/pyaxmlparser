from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.utils import get_zip_file, getxml_value


class APK:

    def __init__(self, apk):
        self.apk = apk
        self.zip_file = get_zip_file(apk)
        self.validate()
        self.axml = AXMLPrinter(self.zip_file.read('AndroidManifest.xml'))
        self.xml = self.axml.get_xml_obj()
        self.arsc = ARSCParser(self.zip_file.read('resources.arsc'))

    def validate(self):
        zip_files = set(self.zip_file.namelist())
        required_files = {'AndroidManifest.xml', 'resources.arsc'}
        assert required_files.issubset(zip_files)

    @property
    def application(self):
        app_name_hex = self.xml.getElementsByTagName(
            "application")[0].getAttribute("android:label")
        if not app_name_hex.startswith('@'):
            return app_name_hex
        _pkg_name = self.arsc.get_packages_names()[0]
        app_name = self.get_resource(app_name_hex, _pkg_name)
        if app_name:
            return app_name
        return self.package

    @property
    def version_name(self):
        version_name = getxml_value(self.xml.documentElement, "versionName")
        if not version_name.startswith("@"):
            return version_name
        rsc = self.get_resource(version_name, self.package)
        if rsc:
            version_name = rsc
        return version_name

    def get_resource(self, key, value):
        try:
            key = '0x' + key[1:]
            hex_value = self.arsc.get_id(value, int(key, 0))[1]
            rsc = self.arsc.get_string(value, hex_value)[1]
        except:
            rsc = None
        return rsc

    @property
    def version_code(self):
        version_code = getxml_value(self.xml.documentElement, "versionCode")
        return version_code

    @property
    def package(self):
        return self.xml.documentElement.getAttribute("package")

    @property
    def icon_info(self):
        icon_type, icon_name = None, None
        app = self.xml.getElementsByTagName('application')[0]
        app_icon = app.getAttribute('android:icon')[1:] or app.getAttribute('androidicon')[1:]

        if app_icon:
            icon_id = int('0x' + app_icon, 0)
            icon_data = self.arsc.get_id(self.package, icon_id)
            if icon_data:
                icon_type, icon_name = icon_data[0], icon_data[1]
        return icon_type, icon_name

    @property
    def icon_data(self):
        icon_type, icon_name = self.icon_info

        if not icon_name:
            return

        if icon_type and 'mipmap' in icon_type:
            search_path = 'res/mipmap'
        else:
            search_path = 'res/drawable'

        for filename in self.zip_file.namelist():
            if filename.startswith(search_path):
                if icon_name in filename.split('/')[-1].rsplit('.', 1):
                    icon_data = self.zip_file.read(filename)
                    return icon_data
