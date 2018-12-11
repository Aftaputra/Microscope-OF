from openflexure_microscope.api.utilities import parse_payload
from openflexure_microscope.api.v1.views import MicroscopeView

from flask import request, Response

import logging


class PluginTestAPI(MicroscopeView):

    def get(self):
        data = self.microscope.plugin.test1.run()  # Call a method from our plugin
        return Response(data)

    def post(self):
        # Get payload
        state = parse_payload(request)
        logging.debug(state)

        # Handle absolute positioning
        if 'data' in state:  # If value is given in payload JSON
            data = str(state['data'])  # Process and store that value

        return Response(data)

ENDPOINTS = {
    'test1': PluginTestAPI
}
