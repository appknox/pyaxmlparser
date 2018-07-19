from pyaxmlparser.arscparser import ARSCParser
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.arscutil import ARSCResTableConfig
from pyaxmlparser.utils import get_zip_file, NS_ANDROID
from warnings import warn


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

    def get_element(self, tag_name, attribute, **attribute_filter):
        """
        Return element in xml files which match with the tag name and the
        specific attribute
        :param tag_name: specify the tag name
        :type tag_name: string
        :param attribute: specify the attribute
        :type attribute: string
        :rtype: string
        """
        tag = self.xml.findall('.//' + tag_name)
        if len(tag) == 0:
            return None
        for item in tag:
            skip_this_item = False
            for attr, val in list(attribute_filter.items()):
                attr_val = item.get(NS_ANDROID + attr)
                if attr_val != val:
                    skip_this_item = True
                    break

            if skip_this_item:
                continue

            value = item.get(NS_ANDROID + attribute)

            if value is not None:
                return value
        return None

    def _format_value(self, value):
        """
        Format a value with packagename, if not already set
        :param value:
        :return:
        """
        if len(value) > 0:
            if value[0] == ".":
                value = self.package + value
            else:
                v_dot = value.find(".")
                if v_dot == 0:
                    value = self.package + "." + value
                elif v_dot == -1:
                    value = self.package + "." + value
        return value

    def get_main_activity(self):
        """
        Return the name of the main activity
        This value is read from the AndroidManifest.xml
        :rtype: str
        """
        x = set()
        y = set()

        activities_and_aliases = self.xml.findall(".//activity") + \
            self.xml.findall(".//activity-alias")

        for item in activities_and_aliases:
            # Some applications have more than one MAIN activity.
            # For example: paid and free content
            activityEnabled = item.get(NS_ANDROID + "enabled")
            if activityEnabled is not None and \
                    activityEnabled != "" and activityEnabled == "false":
                continue

            for sitem in item.findall(".//action"):
                val = sitem.get(NS_ANDROID + "name")
                if val == "android.intent.action.MAIN":
                    x.add(item.get(NS_ANDROID + "name"))

            for sitem in item.findall(".//category"):
                val = sitem.get(NS_ANDROID + "name")
                if val == "android.intent.category.LAUNCHER":
                    y.add(item.get(NS_ANDROID + "name"))

        z = x.intersection(y)
        if len(z) > 0:
            return self._format_value(z.pop())
        return None

    @property
    def application(self):
        """
        Return the appname of the APK
        This name is read from the AndroidManifest.xml
        using the application android:label.
        If no label exists, the android:label of the main activity is used.
        If there is also no main activity label, an empty string is returned.
        :rtype: :class:`str`
        """

        app_name = self.get_element('application', 'label')
        if not app_name:
            main_activity_name = self.get_main_activity()
            app_name = self.get_element(
                'activity', 'label', name=main_activity_name)

        if app_name is None:
            # No App name set
            # TODO return packagename instead?
            return self.package
        if app_name.startswith("@"):
            res_id = int(app_name[1:], 16)
            res_parser = self.arsc

            try:
                app_name = res_parser.get_resolved_res_configs(
                    res_id,
                    ARSCResTableConfig.default_config())[0][1]
            except Exception as e:
                warn("Exception selecting app name: %s" % e)
                app_name = self.package
        return app_name

    @property
    def version_name(self):
        version_name = self.xml.get(NS_ANDROID + "versionName")
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
        except Exception as e:
            warn(str(e))
            rsc = None
        return rsc

    @property
    def version_code(self):
        version_code = self.xml.get(NS_ANDROID + "versionCode")
        return version_code

    @property
    def package(self):
        return self.xml.get("package")

    @property
    def icon_info(self):
        icon_type, icon_name = None, None
        app = self.xml.findall('.//application')[0]
        app_icon = app.get(NS_ANDROID + 'icon')[1:]

        if app_icon:
            icon_id = int('0x' + app_icon, 0)
            icon_data = self.arsc.get_id(self.package, icon_id)
            if icon_data:
                icon_type, icon_name = icon_data[0], icon_data[1]
        return icon_type, icon_name

    @property
    def icon_data(self):

        max_dpi = 65536
        main_activity_name = self.get_main_activity()

        app_icon = self.get_element('activity', 'icon', name=main_activity_name)

        if not app_icon:
            app_icon = self.get_element('application', 'icon')

        if not app_icon:
            res_id = self.arsc.get_res_id_by_key(
                self.package, 'mipmap', 'ic_launcher')
            if res_id:
                app_icon = "@%x" % res_id

        if not app_icon:
            res_id = self.arsc.get_res_id_by_key(
                self.package, 'drawable', 'ic_launcher')
            if res_id:
                app_icon = "@%x" % res_id

        if not app_icon:
            # If the icon can not be found, return now
            return None

        if app_icon.startswith("@"):
            res_id = int(app_icon[1:], 16)
            res_parser = self.arsc
            candidates = res_parser.get_resolved_res_configs(res_id)

            app_icon = None
            current_dpi = -1

            try:
                for config, file_name in candidates:
                    dpi = config.get_density()
                    if current_dpi < dpi <= max_dpi:
                        app_icon = file_name
                        current_dpi = dpi
            except Exception as e:
                warn("Exception selecting app icon: %s" % e)

        return self.zip_file.read(app_icon)

    @property
    def get_min_sdk_version(self):
        return self.get_element("uses-sdk", "minSdkVersion")

    @property
    def get_max_sdk_version(self):
        return self.get_element("uses-sdk", "maxSdkVersion")

    @property
    def get_target_sdk_version(self):
        return self.get_element("uses-sdk", "targetSdkVersion")

    @property
    def get_effective_target_sdk_version(self):
        """
    Return the effective targetSdkVersion, always returns int > 0.
    If the targetSdkVersion is not set, it defaults to 1.  This is
    set based on defaults as defined in:
    https://developer.android.com/guide/topics/manifest/uses-sdk-element.html
    :rtype: int
        """
        target_sdk_version = self.get_target_sdk_version
        if not target_sdk_version:
            target_sdk_version = self.get_min_sdk_version
        try:
            return int(target_sdk_version)
        except (ValueError, TypeError):
            return 1
