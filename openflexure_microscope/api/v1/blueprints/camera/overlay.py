from openflexure_microscope.api.v1.views import MicroscopeView
from openflexure_microscope.api.utilities import JsonPayload

from flask import Response, Blueprint, jsonify, request, abort, url_for, redirect, send_file

class OverlayAPI(MicroscopeView):

    def post(self):
        """
        Set overlay text

        .. :quickref: Overlay; Set camera overlay text

        **Example requests**:

        .. sourcecode:: http

          POST /camera/overlay HTTP/1.1
          Accept: application/json

          {
            "text": "2019/01/15 14:48", 
            "size": 50 
          }

        :>header Accept: application/json

        :<header Content-Type: application/json
        :status 200: preview started/stopped
        """
        
        payload = JsonPayload(request)
        text = payload.param('text', default="", convert=str)
        size = payload.param('size', default=50, convert=int)

        self.microscope.camera.camera.annotate_text = text
        self.microscope.camera.camera.annotate_text_size = size

        return jsonify({'text': text, 'size': size})