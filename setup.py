"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name="openflexure-microscope-server",
    version="2.9.3",
    description="Python module, and Flask-based web API, to run the OpenFlexure Microscope.",
    long_description=long_description,  # Optional, read from README.md
    # Denotes that our long_description is in Markdown; valid values are
    long_description_content_type="text/markdown",  # Optional (see note above)
    # This should be a valid link to your project's main homepage.
    #
    # This field corresponds to the "Home-Page" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#home-page-optional
    url="https://www.openflexure.org",  # Optional
    # This should be your name or the name of the organization which owns the
    # project.
    author="Joel Collins, Richard Bowman, Julian Stirling",  # Optional
    # This should be a valid email address corresponding to the author listed
    # above.
    author_email="contact@openflexure.org",  # Optional
    # Classifiers help users find your project by categorizing it.
    #
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[  # Optional
        #        # How mature is this project? Common values are
        #        #   3 - Alpha
        #        #   4 - Beta
        #        #   5 - Production/Stable
        #        "Development Status :: 3 - Alpha",
        #        # Indicate who your project is intended for
        #        "Intended Audience :: Developers",
        #        "Topic :: Software Development :: Build Tools",
        #        # Pick your license as you wish
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        #        # Specify the Python versions you support here. In particular, ensure
        #        # that you indicate whether you support Python 2, Python 3 or both.
        #        # These classifiers are *not* checked by 'pip install'. See instead
        #        # 'python_requires' below.
        #        "Programming Language :: Python :: 2",
        #        "Programming Language :: Python :: 2.7",
        #        "Programming Language :: Python :: 3",
        #        "Programming Language :: Python :: 3.5",
        #        "Programming Language :: Python :: 3.6",
        #        "Programming Language :: Python :: 3.7",
    ],
    # This field adds keywords for your project which will appear on the
    # project page. What does your project relate to?
    #
    # Note that this is a string of words separated by whitespace, not a list.
    keywords="raspberry pi arduino microscope",  # Optional
    packages=find_packages(
        exclude=["contrib", "docs", "tests", "*node_modules*"]
    ),  # Required
    # Specify which Python versions you support
    python_requires="== 3.7.*",
    # This field lists other packages that your project depends on to run.
    # Any package you put here will be installed by pip when your project is
    # installed, so they must be valid existing projects.
    #
    # For an analysis of "install_requires" vs pip's requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        "Flask ~= 1.0",
        "Pillow ~= 7.2.0",
        "numpy ~= 1.20",
        "scipy ~= 1.6.1",
        "python-dateutil ~= 2.8",
        "psutil ~= 5.6.7",  # Autostorage extension
        "opencv-python-headless ~= 4.5.1",
        "sangaboard ~= 0.2",
        "expiringdict ~= 1.2.1",
        "camera-stage-mapping == 0.1.4",
        "picamerax ~= 20.9.1",
        "pyyaml ~= 5.4.0",
        "pytest-cov ~= 2.10.1",
        "piexif ~= 1.1.3",
        "labthings ~= 1.2.2",
        "typing-extensions ~= 3.7.4",  # Needed for some type-hints in Python < 3.8 (e.g. Literal)
        "RPi.GPIO ~= 0.7.0; platform_machine == 'armv7l'",
    ],  # Optional
    # List additional groups of dependencies here (e.g. development
    # dependencies). Users will be able to install these using the "extras"
    # syntax, for example:
    #
    #   $ pip install sampleproject[dev]
    #
    # Similar to `install_requires` above, these must be valid existing
    # projects.
    extras_require={
        "dev": [
            "sphinxcontrib-httpdomain ~= 1.7",
            "rope ~= 0.14.0",
            "pylint ~= 2.3",
            "pytest ~= 6.1.2",
            "mypy ~= 0.790",
            "poethepoet ~= 0.10.0",
            "freezegun ~= 1.0.0",
            "lxml ~= 4.6",
            "black == 18.9b0",
        ]
    },  # Optional
    # If there are data files included in your packages that need to be
    # installed, specify them here.
    #
    # Sometimes you’ll want to use packages that are properly arranged with
    # setuptools, but are not published to PyPI. In those cases, you can specify
    # a list of one or more dependency_links URLs where the package can
    # be downloaded, along with some additional hints, and setuptools
    # will find and install the package correctly.
    # see https://python-packaging.readthedocs.io/en/latest/dependencies.html#packages-not-on-pypi
    #
    dependency_links=[],
    # If using Python 2.6 or earlier, then these have to be included in
    # MANIFEST.in as well.
    # package_data={"sample": ["package_data.dat"]},  # Optional
    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    #
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[("my_data", ["data/data_file"])],  # Optional
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # `pip` to create the appropriate form of executable for the target
    # platform.
    #
    # For example, the following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    entry_points={
        "console_scripts": [
            "ofm-serve=openflexure_microscope.api.app:ofm_serve",
            "ofm-rescue=openflexure_microscope.rescue.auto:main",
        ]
    },  # Optional
    # List additional URLs that are relevant to your project as a dict.
    #
    # This field corresponds to the "Project-URL" metadata fields:
    # https://packaging.python.org/specifications/core-metadata/#project-url-multiple-use
    #
    # Examples listed include a pattern for specifying where the package tracks
    # issues, where the source is hosted, where to say thanks to the package
    # maintainers, and where to support the project financially. The key is
    # what's used to render the link text on PyPI.
    project_urls={  # Optional
        "Source": "https://gitlab.com/openflexure/openflexure-microscope-server"
    },
)
