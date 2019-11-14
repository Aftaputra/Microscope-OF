from openflexure_microscope.api.utilities import gen, JsonResponse
from openflexure_microscope.api.views import MicroscopeView

from flask import Response, Blueprint, jsonify, request


class StreamAPI(MicroscopeView):
    def get(self):
        """
        Real-time MJPEG stream from the microscope camera

        .. :quickref: Stream; Camera MJPEG stream

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
    def get(self):
        """
        Single snapshot from the camera stream

        .. :quickref: Stream; Camera snapshot

        :>header Accept: image/jpeg
        :>header Content-Type: image/jpeg
        :status 200: stream active
        """
        # Restart stream worker thread
        self.microscope.camera.start_worker()

        return Response(self.microscope.camera.get_frame(), mimetype="image/jpeg")


def construct_blueprint(microscope_obj):

    blueprint = Blueprint("v2_stream_blueprint", __name__)

    blueprint.add_url_rule(
        "/stream", view_func=StreamAPI.as_view("stream", microscope=microscope_obj)
    )

    blueprint.add_url_rule(
        "/snapshot",
        view_func=SnapshotAPI.as_view("snapshot", microscope=microscope_obj),
    )

    return blueprint
