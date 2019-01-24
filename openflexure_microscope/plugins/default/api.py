from openflexure_microscope.api.v1.views import MicroscopeViewPlugin

from flask import request, Response, escape

import logging


class IdentifyAPI(MicroscopeViewPlugin):
    """
    A simple example API plugin, attached through the main microscope plugin.
    """
    def get(self):
        """
        Default plugin to return a plaintext representation of the camera and stage objects.

        .. :quickref: Default plugin; Identify hardware
        """
        data = self.microscope.plugin.default.identify()  # Call a method from our plugin, using the full route
        return Response(escape(data))