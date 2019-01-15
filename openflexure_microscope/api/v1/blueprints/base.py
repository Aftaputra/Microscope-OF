from openflexure_microscope.api.utilities import gen, JsonPayload
from openflexure_microscope.api.v1.views import MicroscopeView

from flask import Response, Blueprint, jsonify, request


class StreamAPI(MicroscopeView):

    def get(self):
        """
        Real-time MJPEG stream from the microscope camera

        .. :quickref: State; Camera stream

        :>header Accept: image/jpeg
        :>header Content-Type: image/jpeg
        :status 200: stream active
        """
        # Restart stream worker thread
        self.microscope.camera.start_worker()

        return Response(
            gen(self.microscope.camera),
            mimetype='multipart/x-mixed-replace; boundary=frame')


class StateAPI(MicroscopeView):

    def get(self):
        """
        JSON representation of the microscope object.

        .. :quickref: State; Microscope state

        **Example request**:

        .. sourcecode:: http

          GET /state/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "camera": {
                "preview_active": false, 
                "record_active": false, 
                "stream_active": true
            }, 
            "plugin": {}, 
            "stage": {
                "backlash": {
                    "x": 128, 
                    "y": 128, 
                    "z": 128
                }, 
                "position": {
                    "x": -8080, 
                    "y": 5665, 
                    "z": -12600
                }
            }
          }

        :>header Accept: application/json
        :>header Content-Type: application/json
        :status 200: state available
        """
        return jsonify(self.microscope.state)


class ConfigAPI(MicroscopeView):

    def get(self):
        """
        JSON representation of the microscope config.

        .. :quickref: Config; Get microscope config

        **Example request**:

        .. sourcecode:: http

          GET /config/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "analog_gain": 1.0, 
            "digital_gain": 1.0, 
            "image_resolution": [
                2592, 
                1944
            ], 
            "jpeg_quality": 75, 
            "name": "0e2c6fac5421429aac67c7903107bdd8", 
            "numpy_resolution": [
                1312, 
                976
            ], 
            "picamera_params": {
                "awb_gains": [
                0.92578125, 
                2.94921875
                ], 
                "awb_mode": "off", 
                "exposure_mode": "off", 
                "framerate": 24.0, 
                "saturation": 0, 
                "shutter_speed": 5378
            }, 
            "plugins": [
                "openflexure_microscope.plugins.default:Plugin"
            ], 
            "shading_table_path": "/home/pi/.openflexure/microscopelst.npy", 
            "video_resolution": [
                832, 
                624
            ]
          }

        :>header Accept: application/json
        :>header Content-Type: application/json
        :status 200: state available
        """
        return jsonify(self.microscope.config)

    def post(self):
        """
        Modify microscope configuration

        .. :quickref: Config; Set microscope config

        **Example request**:

        .. sourcecode:: http

          POST /config HTTP/1.1
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

        :<header Content-Type: application/json
        :status 200: capture created

        """
        payload = JsonPayload(request)

        print(payload.json)

        self.microscope.config = payload.json

        return jsonify(self.microscope.config)

def construct_blueprint(microscope_obj):

    blueprint = Blueprint('base_blueprint', __name__)

    blueprint.add_url_rule(
        '/stream',
        view_func=StreamAPI.as_view('stream', microscope=microscope_obj)
    )

    blueprint.add_url_rule(
        '/state',
        view_func=StateAPI.as_view('state', microscope=microscope_obj)
    )

    blueprint.add_url_rule(
        '/config',
        view_func=ConfigAPI.as_view('config', microscope=microscope_obj)
    )

    return(blueprint)
