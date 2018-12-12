from openflexure_microscope.api.utilities import parse_payload, get_from_payload, gen, get_bool
from openflexure_microscope.api.v1.views import MicroscopeView

from flask import Response, Blueprint, jsonify, request, abort, url_for, redirect, send_file

import logging


class GPUPreviewAPI(MicroscopeView):

    def post(self, operation):
        """
        Create a new image capture.

        .. :quickref: GPU Preview; Start/stop preview

        **Example requests**:

        .. sourcecode:: http

          POST /camera/preview/start HTTP/1.1
          Accept: application/json

        .. sourcecode:: http

          POST /camera/preview/stop HTTP/1.1
          Accept: application/json

        :>header Accept: application/json

        :<header Content-Type: application/json
        :status 200: preview started/stopped
        """
        if operation == "start":
            self.microscope.camera.start_preview()
        elif operation == "stop":
            self.microscope.camera.stop_preview()
        return jsonify(self.microscope.state)
