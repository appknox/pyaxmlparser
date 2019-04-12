# -*- coding: utf-8 -*-

import io
import os
from zipfile import ZipFile, is_zipfile
from struct import unpack, pack

try:
    from .bytecode import BuffHandle
    from . import constants as const
except (ValueError, ImportError):
    from bytecode import BuffHandle
    import constants as const


NS_ANDROID_URI = "http://schemas.android.com/apk/res/android"
NS_ANDROID = "{http://schemas.android.com/apk/res/android}"


def _range(a, b, step=None):
    if step is None:
        return range(int(a), int(b))
    return range(int(a), int(b), step)


def get_zip_file(resource):
    try:
        is_zip = is_zipfile(resource)
    except Exception:
        is_zip = False
    if is_zip:
        return ZipFile(resource)
    if isinstance(resource, (bytes, str)):
        return ZipFile(
            io.BytesIO(resource if isinstance(resource, bytes) else resource.encode())
        )
    raise TypeError("Resource should be file or bytes stream")


def is_str(item, string=False):
    return str(item) if string else item


def complex_to_float(value):
    # complexToFloat from https://github.com/aosp-mirror/platform_frameworks_base/blob/master/core/java/android/util/TypedValue.java
    # result = float(value & (const.COMPLEX_MANTISSA_MASK << const.COMPLEX_MANTISSA_SHIFT)) * const.RADIX_MULTS[
    #     (value >> const.COMPLEX_RADIX_SHIFT) & const.COMPLEX_RADIX_MASK]
    return float(value & 0xFFFFFF00) * const.RADIX_MULTS[(value >> 4) & 3]


def long_to_int(input_l):
    if input_l > 0x7FFFFFFF:
        input_l = (0x7FFFFFFF & input_l) - 0x80000000
    return input_l


def get_package(i):
    return "android:" if i >> 24 == 1 else ""


def format_value(_type, _data, lookup_string=lambda ix: "<string>"):
    if _type == const.TYPE_STRING:
        return lookup_string(_data)

    elif _type == const.TYPE_ATTRIBUTE:
        return "?%s%08X" % (get_package(_data), _data)

    elif _type == const.TYPE_REFERENCE:
        return "@%s%08X" % (get_package(_data), _data)

    elif _type == const.TYPE_FLOAT:
        return "%f" % unpack("=f", pack("=L", _data))[0]

    elif _type == const.TYPE_INT_HEX:
        return "0x%08X" % _data

    elif _type == const.TYPE_INT_BOOLEAN:
        return "false" if _data == 0 else "true"

    elif _type == const.TYPE_DIMENSION:
        return "%f%s" % (
            complex_to_float(_data),
            const.DIMENSION_UNITS[_data & const.COMPLEX_UNIT_MASK],
        )

    elif _type == const.TYPE_FRACTION:
        return "%f%s" % (
            complex_to_float(_data) * 100,
            const.FRACTION_UNITS[_data & const.COMPLEX_UNIT_MASK],
        )

    elif const.TYPE_FIRST_COLOR_INT <= _type <= const.TYPE_LAST_COLOR_INT:
        return "#%08X" % _data

    elif const.TYPE_FIRST_INT <= _type <= const.TYPE_LAST_INT:
        return "%d" % long_to_int(_data)

    return "<0x%X, type 0x%02X>" % (_data, _type)


def string_to_int(target_string=None, base=10):
    result = None
    if isinstance(target_string, (bytes, str)):
        number_symbols = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        try:
            result = int(
                "0" + "".join([x for x in target_string if x in number_symbols]), base
            )
        except ValueError:
            pass
    return result


def get_buffer(raw_buff=None, target="AndroidManifest.xml"):
    data = b""

    if hasattr(raw_buff, "read"):
        data = raw_buff.read()
    else:
        path_to_file = None
        try:
            if os.path.exists(raw_buff):
                path_to_file = raw_buff
        except BaseException:
            pass
        if path_to_file:
            if is_zipfile(path_to_file):
                with ZipFile(path_to_file, "r") as apk:
                    if target in apk.namelist():
                        data = apk.read(target)
            else:
                with open(path_to_file, "rb") as xml_file:
                    data = xml_file.read()
        else:
            data = raw_buff

    if not isinstance(data, (bytes, str)):
        raise ValueError
    data = bytearray(data, encoding="utf-8" if isinstance(data, str) else None)
    return BuffHandle(data)


def read(filename, binary=True):
    """
    Open and read a file
    :param filename: filename to open and read
    :param binary: True if the file should be read as binary
    :return: bytes if binary is True, str otherwise
    """
    with open(filename, "rb" if binary else "r") as f:
        return f.read()


def hex_string_to_int(hex_string=None):
    result = 0
    if isinstance(hex_string, (bytes, str)):
        if "-" in hex_string:
            convert_string = "-0x" + hex_string.replace("0x", "")
        else:
            convert_string = "0x" + hex_string.replace("0x", "")
        try:
            result = int(convert_string, 0)
        except ValueError:
            result = 0
    return result
