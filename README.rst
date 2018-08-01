axmlparser
===========


A simple parser to parse Android XML file.


Usage
======


CLI :
====

.. code-block:: shell

    $ apkinfo ~/Downloads/com.hardcodedjoy.roboremo.15.apk
    APK: /home/chillaranand/Downloads/com.hardcodedjoy.roboremo.15.apk
    App name: RoboRemo
    Package: com.hardcodedjoy.roboremo
    Version name: 2.0.0
    Version code: 15



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
