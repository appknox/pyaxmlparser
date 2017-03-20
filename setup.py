from setuptools import find_packages, setup


dependencies = open('requirements.txt').read().splitlines()

with open('README.rst') as fh:
    long_description = fh.read()


setup(
    name='pyaxmlparser',
    version='0.1.5',
    url='https://github.com/appknox/pyaxmlparser',

    author='Appknox',
    author_email='engineering@appknox.com',

    description='A simple parser to parse Android XML file',
    long_description=long_description,

    packages=find_packages(exclude=['tests']),
    zip_safe=False,
    platforms='any',

    install_requires=dependencies,
    py_modules=['pyaxmlparser'],

    keywords='appknox axmlparser arscparser android',
    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',

        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',

        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
