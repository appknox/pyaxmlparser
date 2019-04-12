# -*- coding: utf-8 -*-

import io
from zlib import crc32
import os
import re
import zipfile
import logging
import hashlib

try:
    # Magic is optional
    import magic
except ImportError:
    magic = None
# There are several implementations of magic,
# unfortunately all called magic
# We use this one: https://github.com/ahupp/python-magic/
if not hasattr(magic, "MagicException"):
    magic = None


try:
    from .arscutil import ARSCResTableConfig
    from .arscparser import ARSCParser
    from .axmlprinter import AXMLPrinter
    from .axmlparser import AXMLParser
    from .resources import public
    from .utils import read, format_value, hex_string_to_int
    from . import constants as const
except (ValueError, ImportError):
    from arscutil import ARSCResTableConfig
    from arscparser import ARSCParser
    from axmlprinter import AXMLPrinter
    from axmlparser import AXMLParser
    from resources import public
    from utils import read, format_value, hex_string_to_int
    import constants as const


NS_ANDROID_URI = "http://schemas.android.com/apk/res/android"
NS_ANDROID = "{{{}}}".format(NS_ANDROID_URI)  # Namespace as used by etree

log = logging.getLogger("pyaxmlparser.core")


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class FileNotPresent(Error):
    pass


class BrokenAPKError(Error):
    pass


class APK(object):
    def __init__(
        self,
        filename,
        raw=False,
        magic_file=None,
        skip_analysis=False,
        testzip=False,
        debug=False,
    ):
        """
        This class can access to all elements in an APK file

        example::

            APK("myfile.apk")
            APK(read("myfile.apk"), raw=True)

        :param filename: specify the path of the file, or raw data
        :param raw: specify if the filename is a path or raw data (optional)
        :param magic_file: specify the magic file (not used anymore - legacy only)
        :param skip_analysis: Skip the analysis, e.g. no manifest files are read. (default: False)
        :param testzip: Test the APK for integrity, e.g. if the ZIP file is broken.
        Throw an exception on failure (default False)

        :type filename: string
        :type raw: boolean
        :type magic_file: string
        :type skip_analysis: boolean
        :type testzip: boolean

        """
        self.log = logging.getLogger("pyaxmlparser.core")
        self.log.setLevel(logging.DEBUG if debug else logging.CRITICAL)
        if magic_file:
            self.log.warning(
                "You set magic_file but this parameter is actually unused. You should remove it."
            )

        self._filename = filename

        self.xml = {}
        self.axml = {}
        self.arsc = {}

        self.package = ""
        self.android_version = {}
        self.platform_build_version = {}
        self.permissions = []
        self.uses_permissions = []
        self.declared_permissions = {}
        self._valid_apk = False

        self._files = {}
        self.files_crc32 = {}
        self.permission_module = {}

        if raw is True:
            self.__raw = bytearray(filename)
            self._sha256 = hashlib.sha256(self.__raw).hexdigest()
            # Set the filename to something sane
            self._filename = "raw_apk_sha256:{}".format(self._sha256)
        else:
            self.__raw = bytearray(read(filename))

        self.zip = zipfile.ZipFile(io.BytesIO(self.__raw), mode="r")

        if testzip:
            # Test the zipfile for integrity before continuing.
            # This process might be slow, as the whole file is read.
            # Therefore it is possible to enable it as a separate feature.
            #
            # A short benchmark showed, that testing the zip takes about 10 times longer!
            # e.g. normal zip loading (skip_analysis=True) takes about 0.01s, where
            # testzip takes 0.1s!
            ret = self.zip.testzip()
            if ret is not None:
                # we could print the filename here, but there are zip which are so broken
                # That the filename is either very very long or does not make any sense.
                # Thus we do not do it, the user might find out by using other tools.
                raise BrokenAPKError(
                    "The APK is probably broken: testzip returned an error."
                )

        if not skip_analysis:
            self._apk_analysis()

    def get_name_with_namespace(self, name):
        """
        return the name including the Android namespace
        """
        return NS_ANDROID + name

    def _apk_analysis(self):
        """
        Run analysis on the APK file.

        This method is usually called by __init__ except if skip_analysis is False.
        It will then parse the AndroidManifest.xml and set all fields in the APK class which can be
        extracted from the Manifest.
        """
        i = "AndroidManifest.xml"
        try:
            manifest_data = self.zip.read(i)
        except KeyError:
            self.log.warning("Missing AndroidManifest.xml. Is this an APK file?")
        else:
            ap = AXMLPrinter(manifest_data)

            if not ap.is_valid:
                self.log.error(
                    "Error while parsing AndroidManifest.xml - is the file valid?"
                )
                return

            self.axml[i] = ap
            self.xml[i] = self.axml[i].xml_object

            if self.axml[i].is_packed:
                self.log.warning(
                    "XML Seems to be packed, operations on the AndroidManifest.xml might fail."
                )

            if self.xml[i] is not None:
                if self.xml[i].tag != "manifest":
                    self.log.error(
                        "AndroidManifest.xml does not start with a <manifest> tag! Is this a valid APK?"
                    )
                    return

                self.package = self.get_attribute_value("manifest", "package")
                self.android_version["Code"] = self.get_attribute_value(
                    "manifest", "versionCode"
                )
                self.android_version["Name"] = self.get_attribute_value(
                    "manifest", "versionName"
                )
                self.platform_build_version["Code"] = self.get_attribute_value(
                    "manifest", "platformBuildVersionCode"
                )
                self.platform_build_version["Name"] = self.get_attribute_value(
                    "manifest", "platformBuildVersionName"
                )
                permission = list(
                    self.get_all_attribute_value("uses-permission", "name")
                )
                self.permissions = list(set(self.permissions + permission))

                for uses_permission in self.find_tags("uses-permission"):
                    self.uses_permissions.append(
                        [
                            self.get_value_from_tag(uses_permission, "name"),
                            self._get_permission_maxsdk(uses_permission),
                        ]
                    )

                # getting details of the declared permissions
                for declared_permission_item in self.find_tags("permission"):
                    declared_perm_name = self._get_res_string_value(
                        str(self.get_value_from_tag(declared_permission_item, "name"))
                    )
                    declared_perm_label = self._get_res_string_value(
                        str(self.get_value_from_tag(declared_permission_item, "label"))
                    )
                    declared_perm_description = self._get_res_string_value(
                        str(
                            self.get_value_from_tag(
                                declared_permission_item, "description"
                            )
                        )
                    )
                    declared_permission_group = self._get_res_string_value(
                        str(
                            self.get_value_from_tag(
                                declared_permission_item, "permissionGroup"
                            )
                        )
                    )
                    declared_perm_protection_level = self._get_res_string_value(
                        str(
                            self.get_value_from_tag(
                                declared_permission_item, "protectionLevel"
                            )
                        )
                    )

                    self.declared_permissions[declared_perm_name] = {
                        "label": declared_perm_label,
                        "description": declared_perm_description,
                        "permissionGroup": declared_permission_group,
                        "protectionLevel": declared_perm_protection_level,
                    }

                self._valid_apk = True

    def __getstate__(self):
        """
        Function for pickling APK Objects.

        We remove the zip from the Object, as it is not pickable
        And it does not make any sense to pickle it anyways.

        :return: the picklable APK Object without zip.
        """
        # Upon pickling, we need to remove the ZipFile
        x = self.__dict__
        x["axml"] = str(x["axml"])
        x["xml"] = str(x["xml"])
        del x["zip"]

        return x

    def __setstate__(self, state):
        """
        Load a pickled APK Object and restore the state

        We load the zip file back by reading __raw from the Object.

        :param state: pickled state
        """
        self.__dict__ = state

        self.zip = zipfile.ZipFile(io.BytesIO(self.__raw), mode="r")

    def _get_res_string_value(self, string):
        if not string.startswith("@string/"):
            return string
        string_key = string[9:]

        res_parser = self.get_android_resources()
        if not res_parser:
            return ""
        string_value = ""
        for package_name in res_parser.packages_names():
            extracted_values = res_parser.get_string(package_name, string_key)
            if extracted_values:
                string_value = extracted_values[1]
                break
        return string_value

    def _get_permission_maxsdk(self, item):
        max_sdk_version = None
        try:
            max_sdk_version = int(self.get_value_from_tag(item, "maxSdkVersion"))
        except ValueError:
            self.log.warning(
                "{} is not a valid value for <uses-permission> "
                "maxSdkVersion".format(self.get_max_sdk_version())
            )
        except TypeError:
            pass
        return max_sdk_version

    @property
    def is_valid(self):
        """
        Return true if the APK is valid, false otherwise.
        An APK is seen as valid, if the AndroidManifest.xml could be successful parsed.
        This does not mean that the APK has a valid signature nor that the APK
        can be installed on an Android system.

        :rtype: boolean
        """
        return self._valid_apk

    def get_filename(self):
        """
        Return the filename of the APK

        :rtype: :class:`str`
        """
        return self._filename

    def get_app_name(self):
        """
        Return the appname of the APK

        This name is read from the AndroidManifest.xml
        using the application android:label.
        If no label exists, the android:label of the main activity is used.

        If there is also no main activity label, an empty string is returned.

        :rtype: :class:`str`
        """

        app_name = self.get_attribute_value("application", "label")
        if app_name is None:
            activities = self.get_main_activities()
            main_activity_name = None
            if len(activities) > 0:
                main_activity_name = activities.pop()
            app_name = self.get_attribute_value(
                "activity", "label", name=main_activity_name
            )

        if app_name is None:
            # No App name set
            # TODO return packagename instead?
            self.log.warning(
                "It looks like that no app name is set for the main activity!"
            )
            return ""

        if app_name.startswith("@"):
            res_parser = self.get_android_resources()
            if not res_parser:
                # TODO: What should be the correct return value here?
                return app_name

            res_id, package = res_parser.parse_id(app_name)

            # If the package name is the same as the APK package,
            # we should be able to resolve the ID.
            if package and package != self.get_package():
                if package == "android":
                    # TODO: we can not resolve this, as we lack framework-res.apk
                    # one exception would be when parsing framework-res.apk directly.
                    self.log.warning(
                        "Resource ID with android package name encountered! "
                        "Will not resolve, framework-res.apk would be required."
                    )
                    return app_name
                else:
                    # TODO should look this up, might be in the resources
                    self.log.warning(
                        "Resource ID with Package name '{}' encountered! Will not resolve".format(
                            package
                        )
                    )
                    return app_name

            try:
                app_name = res_parser.get_resolved_res_configs(
                    res_id, ARSCResTableConfig.default_config()
                )[0][1]
            except Exception as e:
                self.log.warning("Exception selecting app name: {}".format(str(e)))
        return app_name

    def get_app_icon(self, max_dpi=65536):
        """
        Return the first icon file name, which density is not greater than max_dpi,
        unless exact icon resolution is set in the manifest, in which case
        return the exact file.

        This information is read from the AndroidManifest.xml

        From https://developer.android.com/guide/practices/screens_support.html
        and https://developer.android.com/ndk/reference/group___configuration.html

        * DEFAULT                             0dpi
        * ldpi (low)                        120dpi
        * mdpi (medium)                     160dpi
        * TV                                213dpi
        * hdpi (high)                       240dpi
        * xhdpi (extra-high)                320dpi
        * xxhdpi (extra-extra-high)         480dpi
        * xxxhdpi (extra-extra-extra-high)  640dpi
        * anydpi                          65534dpi (0xFFFE)
        * nodpi                           65535dpi (0xFFFF)

        There is a difference between nodpi and anydpi:
        nodpi will be used if no other density is specified. Or the density does not match.
        nodpi is the fallback for everything else. If there is a resource that matches the DPI,
        this is used.
        anydpi is also valid for all densities but in this case, anydpi will overrule all other files!
        Therefore anydpi is usually used with vector graphics and with constraints on the API level.
        For example adaptive icons are usually marked as anydpi.

        When it comes now to selecting an icon, there is the following flow:
        1) is there an anydpi icon?
        2) is there an icon for the dpi of the device?
        3) is there a nodpi icon?
        4) (only on very old devices) is there a icon with dpi 0 (the default)

        For more information read here: https://stackoverflow.com/a/34370735/446140

        :rtype: :class:`str`
        """
        main_activity_name = self.get_main_activity()

        app_icon = self.get_attribute_value("activity", "icon", name=main_activity_name)

        if not app_icon:
            app_icon = self.get_attribute_value("application", "icon")

        res_parser = self.get_android_resources()
        if not res_parser:
            # Can not do anything below this point to resolve...
            return None

        if not app_icon:
            res_id = res_parser.get_res_id_by_key(self.package, "mipmap", "ic_launcher")
            if res_id:
                app_icon = "@%x" % res_id

        if not app_icon:
            res_id = res_parser.get_res_id_by_key(
                self.package, "drawable", "ic_launcher"
            )
            if res_id:
                app_icon = "@%x" % res_id

        if not app_icon:
            # If the icon can not be found, return now
            return None

        if app_icon.startswith("@"):
            res_id = int(app_icon[1:], 16)
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
                self.log.warning("Exception selecting app icon: %s" % e)

        return app_icon

    def get_package(self):
        """
        Return the name of the package

        This information is read from the AndroidManifest.xml

        :rtype: :class:`str`
        """
        return self.package

    def get_android_version_code(self):
        """
        Return the android version code

        This information is read from the AndroidManifest.xml

        :rtype: :class:`str`
        """
        return self.android_version["Code"]

    def get_android_version_name(self):
        """
        Return the android version name

        This information is read from the AndroidManifest.xml

        :rtype: :class:`str`
        """
        return self.android_version["Name"]

    def get_files(self):
        """
        Return the file names inside the APK.

        :rtype: a list of :class:`str`
        """
        return self.zip.namelist()

    def get_file_magic_name(self, buffer):
        """
        Return the filetype guessed for a buffer
        :param buffer: bytes
        :return: str of filetype
        """
        magic_type = None
        if magic:
            try:
                magic_type = magic.from_buffer(buffer[:1024])
            except magic.MagicError:
                self.log.exception("Error getting the magic type!")
                magic_type = None
        file_type = magic_type if magic_type else "Unknown"
        if ("Zip" in file_type) or ("(JAR)" in file_type):
            if self.is_android_raw(buffer) == "APK":
                file_type = "Android application package file"
        return file_type

    @staticmethod
    def is_android_raw(raw):
        """
        Returns a string that describes the type of file, for common Android
        specific formats
        """
        val = None

        # We do not check for META-INF/MANIFEST.MF,
        # as you also want to analyze unsigned APKs...
        # AndroidManifest.xml should be in every APK.
        # classes.dex and resources.arsc are not required!
        # if raw[0:2] == b"PK" and b'META-INF/MANIFEST.MF' in raw:
        # TODO this check might be still invalid. A ZIP file with stored APK inside would match as well.
        # probably it would be better to rewrite this and add more sanity checks.
        if raw[0:2] == b"PK" and b"AndroidManifest.xml" in raw:
            val = "APK"
        elif raw[0:3] == b"dex":
            val = "DEX"
        elif raw[0:3] == b"dey":
            val = "DEY"
        elif raw[0:4] == b"\x03\x00\x08\x00" or raw[0:4] == b"\x00\x00\x08\x00":
            val = "AXML"
        elif raw[0:4] == b"\x02\x00\x0C\x00":
            val = "ARSC"

        return val

    @property
    def files(self):
        """
        Returns a dictionary of filenames and detected magic type

        :return: dictionary of files and their mime type
        """
        return self.get_files_types()

    def get_files_types(self):
        """
        Return the files inside the APK with their associated types (by using python-magic)

        :rtype: a dictionnary
        """
        if self._files == {}:
            # Generate File Types / CRC List
            for i in self.get_files():
                buffer = self.zip.read(i)
                self.files_crc32[i] = crc32(buffer)
                # FIXME why not use the crc from the zipfile?
                # should be validated as well.
                # crc = self.zip.getinfo(i).CRC
                self._files[i] = self.get_file_magic_name(buffer)

        return self._files

    def get_files_crc32(self):
        """
        Calculates and returns a dictionary of file names and CRC32

        :return: dict of filename: CRC32
        """
        if self.files_crc32 == {}:
            for i in self.get_files():
                buffer = self.zip.read(i)
                self.files_crc32[i] = crc32(buffer)

        return self.files_crc32

    def get_files_information(self):
        """
        Return the files inside the APK with their associated types and crc32

        :rtype: str, str, int
        """
        for k in self.get_files():
            yield k, self.get_files_types()[k], self.get_files_crc32()[k]

    def get_raw(self):
        """
        Return raw bytes of the APK

        :rtype: bytes
        """
        return self.__raw

    def get_file(self, filename):
        """
        Return the raw data of the specified filename
        inside the APK

        :rtype: bytes
        """
        try:
            return self.zip.read(filename)
        except KeyError:
            raise FileNotPresent(filename)

    def get_dex(self):
        """
        Return the raw data of the classes dex file

        This will give you the data of the file called `classes.dex`
        inside the APK. If the APK has multiple DEX files, you need to use :func:`~APK.get_all_dex`.

        :rtype: bytes
        """
        try:
            return self.get_file("classes.dex")
        except FileNotPresent:
            return ""

    def get_dex_names(self):
        """
        Return the names of all DEX files found in the APK.
        This method only accounts for "offical" dex files, i.e. all files
        in the root directory of the APK named classes.dex or classes[0-9]+.dex

        :rtype: a list of str
        """
        dex_name_re = re.compile("classes(\d*).dex")
        return filter(lambda x: dex_name_re.match(x), self.get_files())

    def get_all_dex(self):
        """
        Return the raw data of all classes dex files

        :rtype: a generator of bytes
        """
        for dex_name in self.get_dex_names():
            yield self.get_file(dex_name)

    def is_multidex(self):
        """
        Test if the APK has multiple DEX files

        :return: True if multiple dex found, otherwise False
        """
        dex_name_re = re.compile("^classes(\d+)?.dex$")
        return (
            len(
                [
                    instance
                    for instance in self.get_files()
                    if dex_name_re.search(instance)
                ]
            )
            > 1
        )

    @DeprecationWarning
    def get_elements(self, tag_name, attribute, with_namespace=True):
        """
        Deprecated: use `get_all_attribute_value()` instead
        Return elements in xml files which match with the tag name and the specific attribute
        :param tag_name: a string which specify the tag name
        :param attribute: a string which specify the attribute
        :param with_namespace:
        """
        for i in self.xml:
            if self.xml[i] is None:
                continue
            for item in self.xml[i].findall(".//" + tag_name):
                if with_namespace:
                    value = item.get(self.get_name_with_namespace(attribute))
                else:
                    value = item.get(attribute)
                # There might be an attribute without the namespace
                if value:
                    yield self._format_value(value)

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
                if value.find(".") < 1:
                    value = self.package + "." + value

        return value

    @DeprecationWarning
    def get_element(self, tag_name, attribute, **attribute_filter):
        """
        :Deprecated: use `get_attribute_value()` instead
        Return element in xml files which match with the tag name and the specific attribute
        :param tag_name: specify the tag name
        :type tag_name: string
        :param attribute: specify the attribute
        :type attribute: string
        :rtype: string
        """
        for i in self.xml:
            if self.xml[i] is None:
                continue
            tag = self.xml[i].findall(".//" + tag_name)
            if len(tag) == 0:
                return None
            for item in tag:
                skip_this_item = False
                for attr, val in list(attribute_filter.items()):
                    attr_val = item.get(self.get_name_with_namespace(attr))
                    if attr_val != val:
                        skip_this_item = True
                        break

                if skip_this_item:
                    continue

                value = item.get(self.get_name_with_namespace(attribute))

                if value is not None:
                    return value
        return None

    def get_all_attribute_value(
        self, tag_name, attribute, format_value=True, **attribute_filter
    ):
        """
        Return all the attribute values in xml files which match with the tag name and the specific attribute
        :param tag_name: specify the tag name
        :type tag_name: string
        :param attribute: specify the attribute
        :type attribute: string
        :param format_value: specify if the value needs to be formatted with packagename
        :type format_value: boolean
        """
        tags = self.find_tags(tag_name, **attribute_filter)
        for tag in tags:
            value = tag.get(attribute) or tag.get(
                self.get_name_with_namespace(attribute)
            )
            if value is None:
                continue
            yield self._format_value(value) if format_value else value

    def get_attribute_value(
        self, tag_name, attribute, format_value=False, **attribute_filter
    ):
        """
        Return the attribute value in xml files which matches the tag name and the specific attribute
        :param tag_name: specify the tag name
        :type tag_name: string
        :param attribute: specify the attribute
        :type attribute: string
        :param format_value: specify if the value needs to be formatted with packagename
        :type format_value: boolean
        """

        for value in self.get_all_attribute_value(
            tag_name, attribute, format_value, **attribute_filter
        ):
            if value is not None:
                return value

    def get_value_from_tag(self, tag, attribute):
        """
        Return the value of the attribute in a specific tag
        :param tag: specify the tag element
        :type tag: Element
        :param attribute: specify the attribute
        :type attribute: string
        """

        # TODO: figure out if both android:name and name tag exist which one to give preference
        value = tag.get(self.get_name_with_namespace(attribute))
        if value is None:
            self.log.warning(
                "Failed to get the attribute with namespace. "
                "attribute: {}, namespace: {}".format(attribute, NS_ANDROID)
            )
            value = tag.get(attribute)
        return value

    def find_tags(self, tag_name, **attribute_filter):
        """
        Return a list of all the matched tags in all available xml
        :param tag_name: specify the tag name
        :type tag_name: string
        """
        all_tags = [
            self.find_tags_from_xml(i, tag_name, **attribute_filter) for i in self.xml
        ]
        return [tag for tag_list in all_tags for tag in tag_list]

    def find_tags_from_xml(self, xml_name, tag_name, **attribute_filter):
        """
        Return a list of all the matched tags in a specific xml
        :param xml_name: specify from which xml to pick the tag from
        :type xml_name: string
        :param tag_name: specify the tag name
        :type tag_name: string
        """
        xml = self.xml[xml_name]
        if xml is None:
            return []
        if xml.tag == tag_name:
            if self.is_tag_matched(xml.tag, **attribute_filter):
                return [xml]
            return []
        tags = xml.findall(".//" + tag_name)
        return [tag for tag in tags if self.is_tag_matched(tag, **attribute_filter)]

    def is_tag_matched(self, tag, **attribute_filter):
        """
        Return true if the attributes matches in attribute filter
        :param tag: specify the tag element
        :type tag: Element
        :param attribute: specify the attribute
        :type attribute: string
        """
        if len(attribute_filter) <= 0:
            return True
        for attr, value in attribute_filter.items():
            # TODO: figure out if both android:name and name tag exist which one to give preference
            _value = tag.get(self.get_name_with_namespace(attr))
            if _value is None:
                self.log.warning("Failed to get the attribute with namespace")
                _value = tag.get(attr)
            if _value != value:
                return False
        return True

    def get_main_activities(self):
        """
        Return names of the main activities

        These values are read from the AndroidManifest.xml

        :rtype: a set of str
        """
        x = set()
        y = set()

        for i in self.xml:
            if self.xml[i] is None:
                continue
            activities_and_aliases = self.xml[i].findall(".//activity") + self.xml[
                i
            ].findall(".//activity-alias")

            for item in activities_and_aliases:
                # Some applications have more than one MAIN activity.
                # For example: paid and free content
                # Check is activity enabled
                if item.get(self.get_name_with_namespace("enabled")) == "false":
                    continue

                for search_item in item.findall(".//action"):
                    val = search_item.get(self.get_name_with_namespace("name"))
                    if val == "android.intent.action.MAIN":
                        activity = item.get(self.get_name_with_namespace("name"))
                        if activity is not None:
                            x.add(item.get(self.get_name_with_namespace("name")))
                        else:
                            self.log.warning("Main activity without name")

                for search_item in item.findall(".//category"):
                    val = search_item.get(self.get_name_with_namespace("name"))
                    if val == "android.intent.category.LAUNCHER":
                        activity = item.get(self.get_name_with_namespace("name"))
                        if activity is not None:
                            y.add(item.get(self.get_name_with_namespace("name")))
                        else:
                            self.log.warning("Launcher activity without name")

        return x.intersection(y)

    def get_main_activity(self):
        """
        Return the name of the main activity

        This value is read from the AndroidManifest.xml

        :rtype: str
        """
        activities = self.get_main_activities()
        if len(activities) > 0:
            return self._format_value(activities.pop())
        return None

    def get_activities(self):
        """
        Return the android:name attribute of all activities

        :rtype: a list of str
        """
        return list(self.get_all_attribute_value("activity", "name"))

    def get_services(self):
        """
        Return the android:name attribute of all services

        :rtype: a list of str
        """
        return list(self.get_all_attribute_value("service", "name"))

    def get_receivers(self):
        """
        Return the android:name attribute of all receivers

        :rtype: a list of string
        """
        return list(self.get_all_attribute_value("receiver", "name"))

    def get_providers(self):
        """
        Return the android:name attribute of all providers

        :rtype: a list of string
        """
        return list(self.get_all_attribute_value("provider", "name"))

    def get_intent_filters(self, item_type, name):
        """
        Find intent filters for a given item and name.

        Intent filter are attached to activities, services or receivers.
        You can search for the intent filters of such items and get a dictionary of all
        attached actions and intent categories.

        :param item_type: the type of parent item to look for, e.g. `activity`,  `service` or `receiver`
        :param name: the `android:name` of the parent item, e.g. activity name
        :return: a dictionary with the keys `action` and `category` containing the `android:name` of those items
        """
        d = {"action": [], "category": []}

        for i in self.xml:
            # TODO: this can probably be solved using a single xpath
            for item in self.xml[i].findall(".//" + item_type):
                if (
                    self._format_value(item.get(self.get_name_with_namespace("name")))
                    == name
                ):
                    for search_item in item.findall(".//intent-filter"):
                        for action_item in search_item.findall("action"):
                            if (
                                action_item.get(self.get_name_with_namespace("name"))
                                not in d["action"]
                            ):
                                d["action"].append(
                                    action_item.get(
                                        self.get_name_with_namespace("name")
                                    )
                                )
                        for category_item in search_item.findall("category"):
                            if (
                                category_item.get(self.get_name_with_namespace("name"))
                                not in d["category"]
                            ):
                                d["category"].append(
                                    category_item.get(
                                        self.get_name_with_namespace("name")
                                    )
                                )

        if not d["action"]:
            del d["action"]

        if not d["category"]:
            del d["category"]

        return d

    def get_permissions(self):
        """
        Return permissions names declared in the AndroidManifest.xml.

        It is possible that permissions are returned multiple times,
        as this function does not filter the permissions, i.e. it shows you
        exactly what was defined in the AndroidManifest.xml.

        Implied permissions, which are granted automatically, are not returned
        here. Use :meth:`get_uses_implied_permission_list` if you need a list
        of implied permissions.

        :returns: A list of permissions
        :rtype: list
        """
        return self.permissions

    def get_uses_implied_permission_list(self):
        """
            Return all permissions implied by the target SDK or other permissions.

            :rtype: list of string
        """
        target_sdk_version = self.get_effective_target_sdk_version()

        read_call_log = "android.permission.READ_CALL_LOG"
        read_contacts = "android.permission.READ_CONTACTS"
        read_external_storage = "android.permission.READ_EXTERNAL_STORAGE"
        read_phone_state = "android.permission.READ_PHONE_STATE"
        write_call_log = "android.permission.WRITE_CALL_LOG"
        write_contacts = "android.permission.WRITE_CONTACTS"
        write_external_storage = "android.permission.WRITE_EXTERNAL_STORAGE"

        implied = []

        implied_write_external_storage = False
        if target_sdk_version < 4:
            if write_external_storage not in self.permissions:
                implied.append([write_external_storage, None])
                implied_write_external_storage = True
            if read_phone_state not in self.permissions:
                implied.append([read_phone_state, None])

        if (
            write_external_storage in self.permissions or implied_write_external_storage
        ) and read_external_storage not in self.permissions:
            max_sdk_version = None
            for name, version in self.uses_permissions:
                if name == write_external_storage:
                    max_sdk_version = version
                    break
            implied.append([read_external_storage, max_sdk_version])

        if target_sdk_version < 16:
            if (
                read_contacts in self.permissions
                and read_call_log not in self.permissions
            ):
                implied.append([read_call_log, None])
            if (
                write_contacts in self.permissions
                and write_call_log not in self.permissions
            ):
                implied.append([write_call_log, None])

        return implied

    def get_details_permissions(self):
        """
        Return permissions with details

        :rtype: dict of {permission: [protectionLevel, label, description]}
        """
        l = {}

        for i in self.permissions:
            if i in self.permission_module:
                x = self.permission_module[i]
                l[i] = [x["protectionLevel"], x["label"], x["description"]]
            else:
                # FIXME: the permission might be signature, if it is defined by the app itself!
                l[i] = [
                    "normal",
                    "Unknown permission from android reference",
                    "Unknown permission from android reference",
                ]
        return l

    @DeprecationWarning
    def get_requested_permissions(self):
        """
        Returns all requested permissions.

        It has the same result as :meth:`get_permissions` and might be removed in the future

        :rtype: list of str
        """
        return self.get_permissions()

    def get_requested_aosp_permissions(self):
        """
        Returns requested permissions declared within AOSP project.

        This includes several other permissions as well, which are in the platform apps.

        :rtype: list of str
        """
        aosp_permissions = []
        all_permissions = self.get_permissions()
        for perm in all_permissions:
            if perm in list(self.permission_module.keys()):
                aosp_permissions.append(perm)
        return aosp_permissions

    def get_requested_aosp_permissions_details(self):
        """
        Returns requested aosp permissions with details.

        :rtype: dictionary
        """
        permissions = {}
        for permission in self.permissions:
            try:
                permissions[permission] = self.permission_module[permission]
            except KeyError:
                # if we have not found permission do nothing
                continue
        return permissions

    def get_requested_third_party_permissions(self):
        """
        Returns list of requested permissions not declared within AOSP project.

        :rtype: list of strings
        """
        third_party_permissions = []
        all_permissions = self.get_permissions()
        for perm in all_permissions:
            if perm not in list(self.permission_module.keys()):
                third_party_permissions.append(perm)
        return third_party_permissions

    def get_declared_permissions(self):
        """
        Returns list of the declared permissions.

        :rtype: list of strings
        """
        return list(self.declared_permissions.keys())

    def get_declared_permissions_details(self):
        """
        Returns declared permissions with the details.

        :rtype: dict
        """
        return self.declared_permissions

    def get_max_sdk_version(self):
        """
            Return the android:maxSdkVersion attribute

            :rtype: string
        """
        return self.get_attribute_value("uses-sdk", "maxSdkVersion")

    def get_min_sdk_version(self):
        """
            Return the android:minSdkVersion attribute

            :rtype: string
        """
        return self.get_attribute_value("uses-sdk", "minSdkVersion")

    def get_target_sdk_version(self):
        """
            Return the android:targetSdkVersion attribute

            :rtype: string
        """
        return self.get_attribute_value("uses-sdk", "targetSdkVersion")

    def get_effective_target_sdk_version(self):
        """
            Return the effective targetSdkVersion, always returns int > 0.

            If the targetSdkVersion is not set, it defaults to 1.  This is
            set based on defaults as defined in:
            https://developer.android.com/guide/topics/manifest/uses-sdk-element.html

            :rtype: int
        """
        target_sdk_version = self.get_target_sdk_version()
        if not target_sdk_version:
            target_sdk_version = self.get_min_sdk_version()
        try:
            return int(target_sdk_version)
        except (ValueError, TypeError):
            return 1

    def get_libraries(self):
        """
            Return the android:name attributes for libraries

            :rtype: list
        """
        return list(self.get_all_attribute_value("uses-library", "name"))

    def get_features(self):
        """
        Return a list of all android:names found for the tag uses-feature
        in the AndroidManifest.xml

        :return: list
        """
        return list(self.get_all_attribute_value("uses-feature", "name"))

    def is_wearable(self):
        """
        Checks if this application is build for wearables by
        checking if it uses the feature 'android.hardware.type.watch'
        See: https://developer.android.com/training/wearables/apps/creating.html for more information.

        Not every app is setting this feature (not even the example Google provides),
        so it might be wise to not 100% rely on this feature.

        :return: True if wearable, False otherwise
        """
        return "android.hardware.type.watch" in self.get_features()

    def is_leanback(self):
        """
        Checks if this application is build for TV (Leanback support)
        by checkin if it uses the feature 'android.software.leanback'

        :return: True if leanback feature is used, false otherwise
        """
        return "android.software.leanback" in self.get_features()

    def is_androidtv(self):
        """
        Checks if this application does not require a touchscreen,
        as this is the rule to get into the TV section of the Play Store
        See: https://developer.android.com/training/tv/start/start.html for more information.

        :return: True if 'android.hardware.touchscreen' is not required, False otherwise
        """
        return (
            self.get_attribute_value(
                "uses-feature",
                "name",
                required="false",
                name="android.hardware.touchscreen",
            )
            == "android.hardware.touchscreen"
        )

    def new_zip(self, filename, deleted_files=None, new_files=None):
        """
            Create a new zip file

            :param filename: the output filename of the zip
            :param deleted_files: a regex pattern to remove specific file
            :param new_files: a dictionary of new files

            :type filename: string
            :type deleted_files: None or a string
            :type new_files: a dictionary(key:filename, value:content of the file)
        """
        if not isinstance(new_files, dict):
            new_files = {}
        zout = zipfile.ZipFile(filename, "w")

        for item in self.zip.infolist():
            # Block one: deleted_files, or deleted_files and new_files
            if deleted_files is not None:
                if re.match(deleted_files, item.filename) is None:
                    # if the regex of deleted_files doesn't match the filename
                    if new_files is not False:
                        if item.filename in new_files:
                            # and if the filename is in new_files
                            zout.writestr(item, new_files[item.filename])
                            continue
                    # Otherwise, write the original file.
                    buffer = self.zip.read(item.filename)
                    zout.writestr(item, buffer)
            # Block two: deleted_files is None, new_files is not empty
            elif new_files is not False:
                if item.filename in new_files:
                    zout.writestr(item, new_files[item.filename])
                else:
                    buffer = self.zip.read(item.filename)
                    zout.writestr(item, buffer)
            # Block three: deleted_files is None, new_files is empty.
            # Just write out the default zip
            else:
                buffer = self.zip.read(item.filename)
                zout.writestr(item, buffer)
        zout.close()

    def get_android_manifest_axml(self):
        """
            Return the :class:`AXMLPrinter` object which corresponds to the AndroidManifest.xml file

            :rtype: :class:`~androguard.core.bytecodes.axml.AXMLPrinter`
        """
        try:
            return self.axml["AndroidManifest.xml"]
        except KeyError:
            return None

    def get_android_manifest_xml(self):
        """
        Return the parsed xml object which corresponds to the AndroidManifest.xml file

        :rtype: :class:`~lxml.etree.Element`
        """
        try:
            return self.xml["AndroidManifest.xml"]
        except KeyError:
            return None

    def get_android_resources(self):
        """
        Return the :class:`~androguard.core.bytecodes.axml.ARSCParser`
        object which corresponds to the resources.arsc file

        :rtype: :class:`~androguard.core.bytecodes.axml.ARSCParser`
        """
        try:
            return self.arsc["resources.arsc"]
        except KeyError:
            if "resources.arsc" not in self.zip.namelist():
                # There is a rare case, that no resource file is supplied.
                # Maybe it was added manually, thus we check here
                return None
            self.arsc["resources.arsc"] = ARSCParser(self.zip.read("resources.arsc"))
            return self.arsc["resources.arsc"]

    def show(self):
        self.get_files_types()

        print("FILES: ")
        for i in self.get_files():
            try:
                print("\t", i, self._files[i], "%x" % self.files_crc32[i])
            except KeyError:
                print("\t", i, "%x" % self.files_crc32[i])

        print("DECLARED PERMISSIONS:")
        declared_permissions = self.get_declared_permissions()
        for i in declared_permissions:
            print("\t", i)

        print("REQUESTED PERMISSIONS:")
        requested_permissions = self.get_permissions()
        for i in requested_permissions:
            print("\t", i)

        print("MAIN ACTIVITY: ", self.get_main_activity())

        print("ACTIVITIES: ")
        activities = self.get_activities()
        for i in activities:
            filters = self.get_intent_filters("activity", i)
            print("\t", i, filters or "")

        print("SERVICES: ")
        services = self.get_services()
        for i in services:
            filters = self.get_intent_filters("service", i)
            print("\t", i, filters or "")

        print("RECEIVERS: ")
        receivers = self.get_receivers()
        for i in receivers:
            filters = self.get_intent_filters("receiver", i)
            print("\t", i, filters or "")

        print("PROVIDERS: ", self.get_providers())

    @property
    def application(self):
        return self.get_app_name()

    @property
    def packagename(self):
        return self.get_package()

    @property
    def version_name(self):
        return self.get_android_version_name()

    @property
    def version_code(self):
        return self.get_android_version_code()

    @property
    def icon_info(self):
        return self.get_app_icon()

    @property
    def icon_data(self):
        app_icon_file = self.get_app_icon()
        app_icon_data = None
        try:
            app_icon_data = self.get_file(app_icon_file)
        except FileNotPresent:
            try:
                app_icon_data = self.get_file(app_icon_file.encode().decode("cp437"))
            except FileNotPresent:
                pass
        return app_icon_data

    @property
    def gles_version_int(self):
        return self.get_gles_version(to_int=True)

    @property
    def gles_version(self):
        return self.get_gles_version()

    def get_gles_version(self, to_int=False):
        gl_es_version = 0 if to_int else None
        for item in self.get_all_attribute_value(
            "uses-feature", "glEsVersion", format_value=False
        ):
            if not item:
                continue
            gl_es_version = hex_string_to_int(item) if to_int else item
            break
        return gl_es_version

    @property
    def platform_build_version_code(self):
        platform_build_version_code_value = self.platform_build_version.get("Code")
        if not platform_build_version_code_value:
            platform_build_version_code_value = self.get_min_sdk_version()
        return platform_build_version_code_value

    @property
    def platform_build_version_name(self):
        return self.platform_build_version.get("Name", "")


def ensure_final_value(package_name, arsc, value):
    """Ensure incoming value is always the value, not the resid

    androguard will sometimes return the Android "resId" aka
    Resource ID instead of the actual value.  This checks whether
    the value is actually a resId, then performs the Android
    Resource lookup as needed.

    """
    if value:
        return_value = value
        if value[0] == "@":
            try:  # can be a literal value or a resId
                res_id = int("0x" + value[1:], 16)
                res_id = arsc.get_id(package_name, res_id)[1]
                return_value = arsc.get_string(package_name, res_id)[1]
            except (ValueError, TypeError):
                pass
        return return_value
    return ""


def get_apkid(apkfile, logger=None):
    """Read (appid, versionCode, versionName) from an APK

    This first tries to do quick binary XML parsing to just get the
    values that are needed.  It will fallback to full androguard
    parsing, which is slow, if it can't find the versionName value or
    versionName is set to a Android String Resource (e.g. an integer
    hex value that starts with @).

    """
    if not os.path.exists(apkfile):
        if logger and hasattr(logger, "error"):
            logger.error("'{}' does not exist!".format(apkfile))

    app_id = None
    version_code = None
    version_name = None
    with zipfile.ZipFile(apkfile) as apk:
        with apk.open("AndroidManifest.xml") as manifest:
            axml = AXMLParser(manifest.read())
            count = 0
            while axml.is_valid:
                _type = next(axml)
                count += 1
                if _type == const.START_TAG:
                    for i in range(0, axml.get_attribute_count()):
                        name = axml.get_attribute_name(i)
                        _type = axml.get_attribute_value_type(i)
                        _data = axml.get_attribute_value_data(i)
                        value = format_value(
                            _type, _data, lambda _: axml.getAttributeValue(i)
                        )
                        if app_id is None and name == "package":
                            app_id = value
                        elif version_code is None and name == "versionCode":
                            if value.startswith("0x"):
                                version_code = str(int(value, 16))
                            else:
                                version_code = value
                        elif version_name is None and name == "versionName":
                            version_name = value

                    if axml.name == "manifest":
                        break
                elif (
                    _type == const.END_TAG
                    or _type == const.TEXT
                    or _type == const.END_DOCUMENT
                ):
                    raise RuntimeError(
                        "{path}: <manifest> must be the first element in "
                        "AndroidManifest.xml".format(path=apkfile)
                    )

    if not version_name or version_name[0] == "@":
        a = APK(apkfile)
        version_name = ensure_final_value(
            a.package, a.get_android_resources(), a.get_android_version_name()
        )
    if not version_name:
        version_name = ""  # version_name is expected to always be a str

    return app_id, version_code, version_name.strip("\0")
