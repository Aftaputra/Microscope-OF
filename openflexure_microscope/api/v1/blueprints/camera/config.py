from openflexure_microscope.api.utilities import JsonPayload
from openflexure_microscope.api.v1.views import MicroscopeView

from flask import Response, Blueprint, jsonify, request, abort, url_for, redirect, send_file

import logging


class ConfigAPI(MicroscopeView):

    def get(self):
        """
        Get camera configuration

        .. :quickref: Camera config; Get camera configuration
        """

        return jsonify(self.microscope.camera.config)

    def post(self):
        """
        Modify camera configuration

        .. :quickref: Camera config; Set camera configuration

        **Example request**:

        .. sourcecode:: http

          POST /camera/capture HTTP/1.1
          Accept: application/json

          {
            "analog_gain": 1.0, 
            "digital_gain": 1.0, 
            "jpeg_quality": 75, 
            "picamera_params": {
                "framerate": 24.0, 
                "saturation": 0, 
                "shutter_speed": 5000
            }
          }

        :>header Accept: application/json

        :<json float analog_gain: Analog gain
        :<json float digital_gain: Digital gain

        :<json list image_resolution: Image resolution in format [x, y]
        :<json list video_resolution: Video resolution in format [x, y]
        :<json list numpy_resolution: Raw numpy array resolution in format [x, y]

        :<json int jpeg_quality: JPEG quality (1-100)
        :<json string shading_table_path: Full path on the Pi to the lens shading table npy file

        :<json json picamera_param: -   **awb_gains** *(list)*: Auto-white-balance gains in format [r, g, b]
                                        **awb_mode** *(string)*: PiCamera AWB mode
                                        **exposure_mode** *(string)*: PiCamera exposure mode
                                        **framerate** *(float)*: PiCamera framerate
                                        **saturation** *(int)*: PiCamera saturation
                                        **shutter_speed** *(string)*: PiCamera shutter speed

        :<header Content-Type: application/json
        :status 200: capture created

        """
        payload = JsonPayload(request)

        print(payload.json)

        self.microscope.camera.config = payload.json

        return jsonify(self.microscope.camera.config)