from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.utils import get_zip_file


class APK:

    NS_ANDROID_URI = 'http://schemas.android.com/apk/res/android'

    def __init__(self, apk):
        self.apk = apk
        self.zip_file = get_zip_file(apk)
        self.validate()
        self.axml = AXMLPrinter(self.zip_file.read('AndroidManifest.xml')).get_xml_obj()
        self.arsc = ARSCParser(self.zip_file.read('resources.arsc'))

    def validate(self):
        zip_files = set(self.zip_file.namelist())
        required_files = {'AndroidManifest.xml', 'resources.arsc'}
        assert required_files.issubset(zip_files)

    @property
    def application(self):
        app_name_hex = self.axml.getElementsByTagName("application")[0].getAttribute("android:label")
        appnamehex = '0x' + app_name_hex[1:]
        _pkg_name = self.arsc.get_packages_names()[0]
        app_name = self.arsc.get_string(
            _pkg_name,
            self.arsc.get_id(_pkg_name, int(appnamehex, 0))[1]
        )
        return app_name[1]

    @property
    def version_name(self):
        return self.axml.documentElement.getAttributeNS(self.NS_ANDROID_URI, "versionName")

    @property
    def version_code(self):
        return self.axml.documentElement.getAttributeNS(self.NS_ANDROID_URI, "versionCode")

    @property
    def package(self):
        return self.axml.documentElement.getAttribute("package")

    @property
    def icon_info(self):
        icon_hex = '0x' + self.axml.getElementsByTagName('application')[0].getAttribute('android:icon')[1:]
        icon_data = self.arsc.get_id(self.package, int(icon_hex, 0))
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
