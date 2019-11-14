from openflexure_microscope.api.views import MicroscopeView

from flask import Blueprint, jsonify


class StatusAPI(MicroscopeView):
    def get(self):
        """
        JSON representation of the microscope status (read-only properties, modifiable with actions)

        .. :quickref: Status; Microscope status

        **Example request**:

        .. sourcecode:: http

          GET /status/ HTTP/1.1
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
        return jsonify(self.microscope.status)


def construct_blueprint(microscope_obj):

    blueprint = Blueprint("v2_status_blueprint", __name__)

    blueprint.add_url_rule(
        "/", view_func=StatusAPI.as_view("status", microscope=microscope_obj)
    )

    return blueprint
