from openflexure_microscope.plugins import MicroscopePlugin
from openflexure_microscope.api.v1.views import MicroscopeViewPlugin
from openflexure_microscope.api.utilities import JsonPayload

from flask import request, jsonify
import logging

from .recalibrate_utils import recalibrate_camera, auto_expose_and_freeze_settings

API_SCHEMA = {
    'icon': 'lifesaver',
    'requireConnection': True,
    'forms': [
        {
            'route': '/recalibrate',
            'schema': [
                {
                    'fieldType': "htmlBlock",
                    'name': "heading",
                    'content': "<b>This is different form in a plugin!</b>"
                }
            ]
        }
    ]
}

class RecalibrateAPIView(MicroscopeViewPlugin):
    def post(self):
        logging.info("Starting microscope recalibration...")
        task = self.microscope.task.start(self.plugin.recalibrate)

        # Return a handle on the autofocus task
        return jsonify(task.state), 202


class Plugin(MicroscopePlugin):
    """
    A set of default plugins
    """

    api_views = {
        '/recalibrate': RecalibrateAPIView,
    }

    api_schema = API_SCHEMA

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
                scamera.stop_stream_recording(resolution=(640, 480))
            old_resolution = scamera.camera.resolution
            try:
                scamera.camera.resolution = (640, 480)
                auto_expose_and_freeze_settings(scamera.camera)
                recalibrate_camera(scamera.camera)
            finally:
                scamera.camera.resolution = old_resolution
                self.microscope.save_config()
                if streaming:
                    logging.info("Restarting stream after recalibration")
                    scamera.start_stream_recording()
