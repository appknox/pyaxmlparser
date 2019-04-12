import os
import codecs
from setuptools import find_packages, setup
import pyaxmlparser

here = os.path.abspath(os.path.dirname(__file__))


with codecs.open(os.path.join(here, "README.rst"), "r", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name=pyaxmlparser.__package_name__,
    version=pyaxmlparser.__version__,
    url=pyaxmlparser.__url__,
    author=pyaxmlparser.__author__,
    author_email=pyaxmlparser.__author_email__,
    license=pyaxmlparser.__license__,
    packages=find_packages(exclude=["tests", "examples"]),
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    entry_points="""
    [console_scripts]
    apkinfo = pyaxmlparser.__main__:main
    pyaxmlparser = pyaxmlparser.__main__:main
    """,
    py_modules=["pyaxmlparser"],
    description=pyaxmlparser.__description__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="appknox axmlparser arscparser android",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: BSD",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy"
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
