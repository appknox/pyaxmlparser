import io
import os.path
from xml.dom.pulldom import SAX2DOM
from zipfile import ZipFile

import lxml.sax


NS_ANDROID_URI = 'http://schemas.android.com/apk/res/android'
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


def getxml_value(item, attribute, string=False):
    name = is_str(item.getAttributeNS(NS_ANDROID_URI, attribute), string)
    if not name:
        name = is_str(item.getAttribute("android:" + attribute), string)
    return name


def complexToFloat(xcomplex):
    return float(xcomplex & 0xFFFFFF00) * RADIX_MULTS[(xcomplex >> 4) & 3]
