from __future__ import unicode_literals
import io
import sys
from zipfile import ZipFile, is_zipfile
import pyaxmlparser.constants as const
from struct import unpack, pack


NS_ANDROID_URI = 'http://schemas.android.com/apk/res/android'
NS_ANDROID = '{http://schemas.android.com/apk/res/android}'
RADIX_MULTS = [0.00390625, 3.051758E-005, 1.192093E-007, 4.656613E-010]

is_python_3 = sys.version_info > (3, 0, 0)
if is_python_3:
    string_types = (bytes, str)
    text_type = str
else:
    string_types = (bytes, str, unicode)
    text_type = unicode


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
    elif isinstance(resource, bytes):
        return ZipFile(io.BytesIO(resource))
    else:
        raise TypeError('Resource should be file or bytes stream')


def is_str(item, string=False):
    return str(item) if string else item


def complex_to_float(value):
    return float(value & 0xFFFFFF00) * RADIX_MULTS[(value >> 4) & 3]


def long_to_int(input_l):
    if input_l > 0x7fffffff:
        input_l = (0x7fffffff & input_l) - 0x80000000
    return input_l


def get_package(i):
    return 'android:' if i >> 24 == 1 else ''


def format_value(_type, _data, lookup_string=lambda ix: '<string>'):
    if _type == const.TYPE_STRING:
        return lookup_string(_data)

    elif _type == const.TYPE_ATTRIBUTE:
        return '?%s%08X' % (get_package(_data), _data)

    elif _type == const.TYPE_REFERENCE:
        return '@%s%08X' % (get_package(_data), _data)

    elif _type == const.TYPE_FLOAT:
        return '%f' % unpack('=f', pack('=L', _data))[0]

    elif _type == const.TYPE_INT_HEX:
        return '0x%08X' % _data

    elif _type == const.TYPE_INT_BOOLEAN:
        if _data == 0:
            return 'false'
        return 'true'

    elif _type == const.TYPE_DIMENSION:
        return '%f%s' % (
            complex_to_float(_data),
            const.DIMENSION_UNITS[_data & const.COMPLEX_UNIT_MASK]
        )

    elif _type == const.TYPE_FRACTION:
        return '%f%s' % (
            complex_to_float(_data) * 100,
            const.FRACTION_UNITS[_data & const.COMPLEX_UNIT_MASK]
        )

    elif const.TYPE_FIRST_COLOR_INT <= _type <= const.TYPE_LAST_COLOR_INT:
        return '#%08X' % _data

    elif const.TYPE_FIRST_INT <= _type <= const.TYPE_LAST_INT:
        return '%d' % long_to_int(_data)

    return '<0x%X, type 0x%02X>' % (_data, _type)
