axmlparser
===========


A simple parser to parse Android XML file.


Usage
======

Get package name:

.. code-block:: python

    from pyaxmlparser import APK


    apk = APK('/foo/bar.apk')
    apk.validate()
    print(apk.package_name)
