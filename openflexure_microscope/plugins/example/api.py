from openflexure_microscope.api.utilities import JsonPayload
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
        data = self.plugin.identify()  # Call a method from our plugin, using the MicroscopeViewPlugin.plugin shortcut
        return Response(escape(data))


class HelloWorldAPI(MicroscopeViewPlugin):
    """
    A method to create, set, and return a new microscope parameter.
    """

    def get(self):
        """
        Method to call when an HTTP GET request is made.
        """

        # If the microscope does not already contain our plugin_string attribute
        if not hasattr(self.microscope, 'plugin_string'):
            # Make a string, using the MicroscopeViewPlugin.plugin shortcut
            self.microscope.plugin_string = self.plugin.hello_world()

        return Response(self.microscope.plugin_string)

    def post(self):
        """
        Method to call when an HTTP POST request is made. 
        Assumes request will include a JSON payload.
        """
        # Get payload JSON as a dictionary
        payload = JsonPayload(request)

        # Extract a value from the JSON key 'plugin_string'. If no value is given, default to None
        new_plugin_string = payload.param('plugin_string')

        if new_plugin_string:  # If not None or empty
            # Set microscope attribute to the specified string
            self.microscope.plugin_string = new_plugin_string

        return Response(self.microscope.plugin_string)
