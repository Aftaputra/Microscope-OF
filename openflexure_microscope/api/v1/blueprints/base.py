from openflexure_microscope.api.utilities import gen
from openflexure_microscope.api.v1.views import MicroscopeView

from flask import Response, Blueprint, jsonify


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

    return(blueprint)
