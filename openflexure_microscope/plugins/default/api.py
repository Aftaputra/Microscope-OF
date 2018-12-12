from openflexure_microscope.api.utilities import parse_payload
from openflexure_microscope.api.v1.views import MicroscopeViewPlugin

from flask import request, Response, escape

import logging


class IdentifyAPI(MicroscopeViewPlugin):

    def get(self):
        data = self.microscope.plugin.default.identify()  # Call a method from our plugin, using the full route
        return Response(escape(data))


class HelloWorldAPI(MicroscopeViewPlugin):

    def get(self):
        data = self.plugin.hello_world()  # Call a method from our plugin, using the MicroscopeViewPlugin.plugin shortcut
        return Response(data)
