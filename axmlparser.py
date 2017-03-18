#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# vim: fenc=utf-8
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#

'''
File name: axmlparser.py
Version: 0.1
Author: Subho Halder <subho.halder@gmail.com>
Date created: 2015-08-07
'''


from pyaxmlparser.axmlprinter import AXMLPrinter
from pyaxmlparser.arscparser import ARSCParser

f = AXMLPrinter(open("/Users/subho/Desktop/Scans/test/AndroidManifest.xml", 'rb').read())
r = ARSCParser(open("/Users/subho/Desktop/Scans/test/resources.arsc", "rb").read())

appnamethex = f.getElementsByTagName("application")[0].getAttribute("android:label")

appnamehex = '0x' + appnamethex[1:]

app_name = r.get_string(r.get_packages_names()[0], r.get_id(r.get_packages_names()[0], int(appnamehex, 0))[1])

return app_name
