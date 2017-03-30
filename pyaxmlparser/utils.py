import io
import os.path
from xml.dom.pulldom import SAX2DOM
from zipfile import ZipFile

import lxml.sax


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
