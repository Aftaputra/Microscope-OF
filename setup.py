from setuptools import setup, find_packages
from codecs import open
from os import path
import re

__author__ = 'Joel Collins'

HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()


def find_version():
    """Determine the version based on __init__.py."""
    with open(path.join(HERE, "openflexure_microscope", "__init__.py"), 'r') as f:
        init_py = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", init_py, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Couldn't parse version string from __init__.py")

VERSION = find_version()

setup(
    name='openflexure_microscope',
    version=VERSION,
    description='Control scripts for the OpenFlexure Microscope',
    long_description=LONG_DESCRIPTION,
    author='Joel Collins',
    author_email='joel@jtcollins.net',
    packages=find_packages(),
    keywords=['arduino', 'python', 'serial', 'microscope'],
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.5'
        ],
    install_requires=[
        'pyserial',
        'future',
        'openflexure_stage',
        'flask',
        'itsdangerous',
        'Jinja2',
        'MarkupSafe',
        'picamera',
        'Werkzeug',
        'pyyaml',
        'numpy',
        'Pillow',
        'RPi.GPIO',
    ],
)
