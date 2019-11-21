"""
Writeable settings for the microscope, and attached hardware
"""

from openflexure_microscope.api.utilities import gen, JsonResponse
from openflexure_microscope.api.views import MicroscopeView
from openflexure_microscope.api.utilities import blueprint_for_module

from flask import Blueprint, jsonify, request
import logging


class SettingsAPI(MicroscopeView):
    def get(self):
        """
        JSON representation of the microscope settings.

        .. :quickref: Settings; Get microscope settings

        **Example request**:

        .. sourcecode:: http

          GET /settings/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "id": "0e2c6fac5421429aac67c7903107bdd8",
            "name": "docuscope-2000",
            "fov": [4100, 3146],
            "camera_settings": {
                "image_resolution": [2592, 1944],
                "numpy_resolution": [1312, 976],
                "video_resolution": [832, 624],
                "jpeg_quality": 75,
                "picamera_settings": {
                    "analog_gain": 1.0,
                    "digital_gain": 1.0,
                    "awb_gains": [0.92578125, 2.94921875],
                    "awb_mode": "off",
                    "exposure_mode": "off",
                    "framerate": 24.0,
                    "saturation": 0,
                    "shutter_speed": 5378
                },
            },
            "stage_settings": {
                "backlash": {
                    "x": 256,
                    "y": 256,
                    "z": 0
                }
            }
            "plugins": [
                "openflexure_microscope.plugins.default.autofocus:AutofocusPlugin",
                "openflexure_microscope.plugins.default.scan:ScanPlugin",
                "openflexure_microscope.plugins.default.camera_calibration:Plugin"
            ]
          }

        :>header Accept: application/json
        :>header Content-Type: application/json
        :status 200: state available
        """
        return jsonify(self.microscope.read_settings())

    def put(self):
        """
        Modify microscope configuration

        .. :quickref: Config; Set microscope config

        **Example request**:

        .. sourcecode:: http

          PUT /config HTTP/1.1
          Accept: application/json

          {
            "id": "0e2c6fac5421429aac67c7903107bdd8",
            "name": "docuscope-2000",
            "fov": [4100, 3146],
            "camera_settings": {
                "image_resolution": [2592, 1944],
                "numpy_resolution": [1312, 976],
                "video_resolution": [832, 624],
                "jpeg_quality": 75,
                "picamera_settings": {
                    "analog_gain": 1.0,
                    "digital_gain": 1.0,
                    "awb_gains": [0.92578125, 2.94921875],
                    "awb_mode": "off",
                    "exposure_mode": "off",
                    "framerate": 24.0,
                    "saturation": 0,
                    "shutter_speed": 5378
                },
            },
            "stage_settings": {
                "backlash": {
                    "x": 256,
                    "y": 256,
                    "z": 0
                }
            }
            "plugins": [
                "openflexure_microscope.plugins.default.autofocus:AutofocusPlugin",
                "openflexure_microscope.plugins.default.scan:ScanPlugin",
                "openflexure_microscope.plugins.default.camera_calibration:Plugin"
            ]
          }

        :>header Accept: application/json

        :<json string id: Unique string identifier of the microscope.
        :<json string name: Friendly name for the microscope
        :<json array fov: Field of view (motor steps per full width and height of frame)
        :<json json camera_settings:    - **image_resolution** *(array)*: Resolution of full image captures
                                        - **numpy_resolution** *(array)*: Resolution of full numpy array captures
                                        - **video_resolution** *(array)*: Resolution of video recordings, low res image captures, and the preview stream
                                        - **jpeg_quality** *(int)*: Quality in which to store JPEG capture data
                                        - **picamera_settings** *(json)*: Key-value pairs to apply directly to any attached PiCamera object
        :<json json stage_settings:     - **backlash** *(json)*: x, y, and z backlash compensation, in motor steps
        :<json array plugins: Array of plugin paths to load. Requires reloading the microscope object after applying

        :<header Content-Type: application/json
        :status 200: capture created

        """
        payload = JsonResponse(request)

        logging.debug("Updating settings from PUT request:")
        logging.debug(payload.json)

        self.microscope.apply_settings(payload.json)
        self.microscope.save_settings()

        return jsonify(self.microscope.read_settings(json_safe=True))


def construct_blueprint(microscope_obj):

    blueprint = blueprint_for_module(__name__)

    blueprint.add_url_rule(
        "/", view_func=SettingsAPI.as_view("settings", microscope=microscope_obj)
    )

    return blueprint
