from setuptools import find_packages, setup

__VERSION__ = '0.3.17'

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='pyaxmlparser',
    version=__VERSION__,
    url='https://github.com/appknox/pyaxmlparser',

    author='Subho Halder',
    author_email='sunny@appknox.com',
    license='MIT',

    packages=find_packages(exclude=['tests', 'examples']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=['lxml', 'click==6.7'],
    entry_points='''
    [console_scripts]
    apkinfo = pyaxmlparser.cli:main
    ''',
    py_modules=['pyaxmlparser'],
    description="Python3 Parser for Android XML file and get Application Name without using Androguard",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords='appknox axmlparser arscparser android',
    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',

        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
