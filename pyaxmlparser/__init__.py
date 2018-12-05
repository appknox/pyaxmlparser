# flake8: noqa

from pyaxmlparser.core import APK
from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.axmlparser import AXMLParser
from pyaxmlparser.arscparser import ARSCParser

__all__ = (
    '__title__', '__package_name__', '__description__', '__url__', '__version__', '__author__',
    '__author_email__', '__license__', 'APK', 'AXMLPrinter', 'AXMLParser', 'ARSCParser'
)

__title__ = 'Pyaxmlparser'
__package_name__ = 'pyaxmlparser'
__description__ = 'Parser for Android XML file and get Application Name without using Androguard.'
__url__ = 'https://github.com/appknox/pyaxmlparser'
__version__ = '0.3.14'
__author__ = 'Subho Halder'
__author_email__ = 'sunny@appknox.com'
__license__ = 'MIT License'
