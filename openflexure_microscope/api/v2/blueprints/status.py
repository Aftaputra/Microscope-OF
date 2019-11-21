"""
Read-only status of the microscope, and attached hardware info
"""

from openflexure_microscope.api.views import MicroscopeView
from openflexure_microscope.api.utilities import blueprint_for_module
from openflexure_microscope.utilities import get_by_path

from flask import Blueprint, jsonify, abort


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


class NestedStatusAPI(MicroscopeView):
    def get(self, route):

        keys = route.split("/")

        try:
            value = get_by_path(self.microscope.status, keys)
        except KeyError:
            return abort(404)

        return jsonify(value)


def construct_blueprint(microscope_obj):

    blueprint = blueprint_for_module(__name__)

    blueprint.add_url_rule(
        "/", view_func=StatusAPI.as_view("status", microscope=microscope_obj)
    )

    blueprint.add_url_rule(
        "/<path:route>",
        view_func=NestedStatusAPI.as_view("nested_status", microscope=microscope_obj),
    )

    return blueprint
