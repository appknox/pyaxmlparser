Axmlparser
==========

.. image:: https://img.shields.io/pypi/v/pyaxmlparser.svg
   :alt: package version on https://pypi.org
   :target: https://pypi.org/project/pyaxmlparser/

.. image:: https://img.shields.io/pypi/l/pyaxmlparser.svg
   :alt: package license
   :target: https://pypi.org/project/pyaxmlparser/

.. image:: https://img.shields.io/pypi/pyversions/pyaxmlparser.svg
   :alt: requires python versions for package
   :target: https://pypi.org/project/pyaxmlparser/

.. image:: https://img.shields.io/github/contributors/appknox/pyaxmlparser.svg
   :alt: package contributes
   :target: https://github.com/appknox/pyaxmlparser/graphs/contributors


A simple parser to parse Android XML file.


Usage
=====


CLI :
=====

.. code-block:: console

  $ apkinfo ~/Downloads/com.hardcodedjoy.roboremo.15.apk info
  APK: /home/chillaranand/Downloads/com.hardcodedjoy.roboremo.15.apk
    App name: RoboRemo
    Package: com.hardcodedjoy.roboremo
    Version name: 2.0.0
    Version code: 15

  $ pyaxmlparser ~/Downloads/com.hardcodedjoy.roboremo.15.apk info
  APK: /home/chillaranand/Downloads/com.hardcodedjoy.roboremo.15.apk
    App name: RoboRemo
    Package: com.hardcodedjoy.roboremo
    Version name: 2.0.0
    Version code: 15

  $ python -m pyaxmlparser ~/Downloads/com.hardcodedjoy.roboremo.15.apk info
  APK: /home/chillaranand/Downloads/com.hardcodedjoy.roboremo.15.apk
    App name: RoboRemo
    Package: com.hardcodedjoy.roboremo
    Version name: 2.0.0
    Version code: 15

  $ apkinfo ~/Downloads/com.hardcodedjoy.roboremo.15.apk xml
  <manifest ...>
    ...
  </manifest>

  $ apkinfo ~/Downloads/com.hardcodedjoy.roboremo.15.apk xml > "~/manifest.xml"
    (save into ~/manifest.xml output xml)

  $ apkinfo ~/Downloads/com.hardcodedjoy.roboremo.15.apk xml  -o "~/manifest.xml"
    (save into ~/manifest.xml output xml)



Python package :
================

.. code-block:: python

    from pyaxmlparser import APK

    apk = APK('/foo/bar.apk')
    print(apk.package)
    print(apk.version_name)
    print(apk.version_code)
    print(apk.icon_info)
    print(apk.icon_data)
    print(apk.application)

.. code-block:: python

    from pyaxmlparser import AXMLPrinter

    xml = AXMLPrinter('/foo/bar.apk').get_xml_obj()
    print(xml.get('package'))

.. code-block:: python

    from pyaxmlparser import AXMLPrinter

    apk_path = '/foo/bar.apk'
    with open(apk_path, 'rb') as apk_file:
        android_xml = apk_file.read()
        xml, error = AXMLPrinter(android_xml).get_xml_obj()
        if xml is not None:
            print(xml.get('package'))
