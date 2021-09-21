Quickstart
=======================================================

Install
-------

Stable installation
+++++++++++++++++++
The OpenFlexure Microscope software is designed to be run on the embedded Raspberry Pi, in an OpenFlexure Microscope.  For most users, our `pre-built Raspbian SD card image. <https://openflexure.org/projects/microscope/install>`_ is the easiest way to get started.  This SD card image is based on Raspberry Pi OS and includes both the microscope server and OpenFlexure Connect.  A desktop shortcut will directly start OpenFlexure Connect if you are using the Raspberry Pi directly, or the microscope can be controlled over the network with its default hostname `raspberrypi.local`.


Manual installation
+++++++++++++++++++

To install the server on a Raspberry Pi without using the pre-built OpenFlexure Raspbian image, or to install the server on a different system (this is useful for development), follow the instructions in the README file at the top level of the project's repository.

Usage
-----
The easiest way to use the microscope is through OpenFlexure Connect, our cross-platform application that handles discovering and connecting to the microscope.  It is detailed on the `instruction page on our website <https://openflexure.org/projects/microscope/control>`_ including a download link.  OpenFlexure Connect is pre-installed on the full SD card image (not the "lite" image, as this does not have support for a graphical desktop).

If you know the hostname or IP address of your microscope, you can also connect to the same interface using a web browser by entering `http://microscope.local:5000/` as the address.  `microscope.local` is the default hostname of the microscope if you use our pre-built SD card image.  If you know the IP address or have customised the hostname, you can use that instead.  Note that the hostname is announced via mDNS, which is usually reliable if the microscope is connected via a network cable directly to your client computer but may not work if both devices are connected to a more complicated network.  As support for mDNS varies between operating systems, OpenFlexure Connect often detects microscopes even if you cannot resolve the microscope using the mDNS hostname.

Whether you connect with OpenFlexure Connect, or through a web browser, the web application interface is the same.  See the "web application" section of this manual for more details.

Managing the server
-------------------

Managing the server through the installer script's CLI is documented `on our website <https://openflexure.org/projects/microscope/install#managing-the-microscope-server>`_.

This includes starting the server as a background service, as well as starting a development server with real-time debug logging.