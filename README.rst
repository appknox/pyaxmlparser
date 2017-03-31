axmlparser
===========


A simple parser to parse Android XML file.


Usage
======

Get package name:

.. code-block:: python

    from pyaxmlparser import APK


    apk = APK('/foo/bar.apk')
    print(apk.package)
    print(apk.version_name)
    print(apk.version_code)
    print(apk.icon_info)
    print(apk.icon_data)
    print(apk.application)
