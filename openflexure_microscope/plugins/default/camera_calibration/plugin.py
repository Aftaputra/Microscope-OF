import time
import numpy as np

from openflexure_microscope.plugins import MicroscopePlugin
from openflexure_microscope.utilities import set_properties
from openflexure_microscope.api.v1.views import MicroscopeViewPlugin
from openflexure_microscope.api.utilities import JsonPayload

from flask import request, Response, escape, jsonify
import logging

from .recalibrate_utils import recalibrate_camera

class RecalibrateAPIView(MicroscopeViewPlugin):
    def post(self):
        payload = JsonPayload(request)
        
        # Figure out the range of z values to use

        print("Starting microscope recalibration...")
        task = self.microscope.task.start(self.plugin.recalibrate)

        # return a handle on the autofocus task
        return jsonify(task.state, 202)

class Plugin(MicroscopePlugin):
    """
    A set of default plugins
    """

    api_views = {
        '/recalibrate': RecalibrateAPIView,
    }

    def recalibrate(self):
        """Reset the camera's settings.

        This generates new gains, exposure time, and lens shading
        table such that the background is as uniform as possible
        with a gray level of 230.  It takes a little while to run.
        """
        scamera = self.microscope.camera
        with scamera.lock:
            assert not scamera.state['record_active'], "Can't recalibrate while recording!"
            streaming = scamera.state['stream_active']
            if streaming:
                logging.info("Stopping stream before recalibration")
                scamera.stop_stream_recording(resolution=(640,480))
            old_resolution = scamera.camera.resolution
            try:
                scamera.camera.resolution=(640,480)
                recalibrate_camera(scamera.camera)
            finally:
                scamera.camera.resolution=old_resolution
                self.microscope.save_config()
                if streaming:
                    logging.info("Restarting stream after recalibration")
                    scamera.start_stream_recording()


