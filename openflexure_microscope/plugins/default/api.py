import numpy as np

from openflexure_microscope.api.v1.views import MicroscopeViewPlugin
from openflexure_microscope.api.utilities import JsonPayload

from flask import request, Response, escape, jsonify

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

class MeasureSharpnessAPI(MicroscopeViewPlugin):
    def post(self):
        payload = JsonPayload(request)
        return jsonify({'sharpness': self.plugin.measure_sharpness()})

class AutofocusAPI(MicroscopeViewPlugin):
    def post(self):
        payload = JsonPayload(request)
        
        # Figure out the range of z values to use
        dz = payload.param("dz", default=np.linspace(-300,300,7), convert=np.array)

        print("Running autofocus...")
        task = self.microscope.task.start(self.plugin.autofocus, dz)

        # return a handle on the autofocus task
        return jsonify(task.state, 202)
