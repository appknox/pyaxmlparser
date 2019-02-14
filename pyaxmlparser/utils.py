import io
import os.path
from xml.dom.pulldom import SAX2DOM
from zipfile import ZipFile
import pyaxmlparser.constants as const
from struct import unpack, pack

import lxml.sax


NS_ANDROID_URI = 'http://schemas.android.com/apk/res/android'
NS_ANDROID = '{http://schemas.android.com/apk/res/android}'
RADIX_MULTS = [0.00390625, 3.051758E-005, 1.192093E-007, 4.656613E-010]


def parse_lxml_dom(tree):
    handler = SAX2DOM()
    lxml.sax.saxify(tree, handler)
    return handler.document


def _range(a, b, step=None):
    if step is None:
        return range(int(a), int(b))
    return range(int(a), int(b), step)


def get_zip_file(resource):
    if isinstance(resource, bytes):
        return ZipFile(io.BytesIO(resource))
    if os.path.isfile(resource):
        return ZipFile(resource)
    raise TypeError('Resource should be file or bytes stream')


def is_str(item, string=False):
    if string:
        return str(item)
    return item


def complexToFloat(xcomplex):
    return float(xcomplex & 0xFFFFFF00) * RADIX_MULTS[(xcomplex >> 4) & 3]


def long2int(input_l):
    if input_l > 0x7fffffff:
        input_l = (0x7fffffff & input_l) - 0x80000000
    return input_l


def getPackage(i):
    if i >> 24 == 1:
        return "android:"
    return ""


def format_value(_type, _data, lookup_string=lambda ix: "<string>"):
    if _type == const.TYPE_STRING:
        return lookup_string(_data)

    elif _type == const.TYPE_ATTRIBUTE:
        return "?%s%08X" % (getPackage(_data), _data)

    elif _type == const.TYPE_REFERENCE:
        return "@%s%08X" % (getPackage(_data), _data)

    elif _type == const.TYPE_FLOAT:
        return "%f" % unpack("=f", pack("=L", _data))[0]

    elif _type == const.TYPE_INT_HEX:
        return "0x%08X" % _data

    elif _type == const.TYPE_INT_BOOLEAN:
        if _data == 0:
            return "false"
        return "true"

    elif _type == const.TYPE_DIMENSION:
        return "%f%s" % (
            complexToFloat(_data),
            const.DIMENSION_UNITS[_data & const.COMPLEX_UNIT_MASK]
        )

    elif _type == const.TYPE_FRACTION:
        return "%f%s" % (
            complexToFloat(_data) * 100,
            const.FRACTION_UNITS[_data & const.COMPLEX_UNIT_MASK]
        )

    elif const.TYPE_FIRST_COLOR_INT <= _type <= const.TYPE_LAST_COLOR_INT:
        return "#%08X" % _data

    elif const.TYPE_FIRST_INT <= _type <= const.TYPE_LAST_INT:
        return "%d" % long2int(_data)

    return "<0x%X, type 0x%02X>" % (_data, _type)


def read(filename, binary=True):
    """
    Open and read a file
    :param filename: filename to open and read
    :param binary: True if the file should be read as binary
    :return: bytes if binary is True, str otherwise
    """
    with open(filename, 'rb' if binary else 'r') as f:
        return f.read()
