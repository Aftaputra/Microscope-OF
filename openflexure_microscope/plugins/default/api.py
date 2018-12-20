from openflexure_microscope.api.utilities import parse_payload
from openflexure_microscope.api.v1.views import MicroscopeViewPlugin

from flask import request, Response, escape

import logging


class IdentifyAPI(MicroscopeViewPlugin):
    """
    A simple example API plugin, attached through the main microscope plugin.
    """
    def get(self):
        """
        Method to call when an HTTP GET request is made.
        """
        data = self.microscope.plugin.default.identify()  # Call a method from our plugin, using the full route
        return Response(escape(data))


class HelloWorldAPI(MicroscopeViewPlugin):
    """
    An even simpler example API plugin, which just returns static data without using the microscope.
    """
    def get(self):
        """
        Method to call when an HTTP GET request is made.
        """
        data = self.plugin.hello_world()  # Call a method from our plugin, using the MicroscopeViewPlugin.plugin shortcut
        return Response(data)
