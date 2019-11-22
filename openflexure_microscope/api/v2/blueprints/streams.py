"""
Top-level description of routes related to live camera stream data
"""

from openflexure_microscope.api.utilities import gen, JsonResponse
from openflexure_microscope.api.views import MicroscopeView
from openflexure_microscope.api.utilities import (
    blueprint_for_module,
    blueprint_name_for_module,
)
from openflexure_microscope.utilities import description_from_view

from flask import Response, Blueprint, jsonify, request, url_for


class StreamAPI(MicroscopeView):
    def get(self):
        return jsonify(streams_representation())


class MjpegAPI(MicroscopeView):
    """
    Real-time MJPEG stream from the microscope camera
    """

    def get(self):
        """
        Real-time MJPEG stream from the microscope camera

        .. :quickref: Streams; Camera MJPEG stream

        :>header Accept: image/jpeg
        :>header Content-Type: image/jpeg
        :status 200: stream active
        """
        # Restart stream worker thread
        self.microscope.camera.start_worker()

        return Response(
            gen(self.microscope.camera),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )


class SnapshotAPI(MicroscopeView):
    """
    Single JPEG snapshot from the camera stream
    """

    def get(self):
        """
        Single snapshot from the camera stream

        .. :quickref: Streams; Camera snapshot

        :>header Accept: image/jpeg
        :>header Content-Type: image/jpeg
        :status 200: stream active
        """
        # Restart stream worker thread
        self.microscope.camera.start_worker()

        return Response(self.microscope.camera.get_frame(), mimetype="image/jpeg")


_streams = {
    "mjpeg": {"rule": "/mjpeg", "view_class": MjpegAPI, "conditions": True},
    "snapshot": {"rule": "/snapshot", "view_class": SnapshotAPI, "conditions": True},
}


def enabled_streams():
    global _streams
    return {k: v for k, v in _streams.items() if v["conditions"]}


def streams_representation():
    global _streams

    streams = {}
    for name, stream in enabled_streams().items():
        d = {"links": {"self": url_for(f".{name}")}}

        d.update(description_from_view(stream["view_class"]))

        streams[name] = d

    return streams


def construct_blueprint(microscope_obj):

    blueprint = blueprint_for_module(__name__)

    # For each enabled stream route defined in our dictionary above
    for name, stream in enabled_streams().items():
        # Add the action to our blueprint
        blueprint.add_url_rule(
            stream["rule"],
            view_func=stream["view_class"].as_view(name, microscope=microscope_obj),
        )

    blueprint.add_url_rule(
        "/", view_func=StreamAPI.as_view("streams", microscope=microscope_obj)
    )

    return blueprint
