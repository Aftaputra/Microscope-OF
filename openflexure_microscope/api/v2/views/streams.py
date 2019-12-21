from openflexure_microscope.api.utilities import gen, JsonResponse
from openflexure_microscope.utilities import get_by_path, set_by_path, create_from_path

from openflexure_microscope.common.flask_labthings.find import find_device
from openflexure_microscope.common.flask_labthings.resource import Resource

from flask import jsonify, request, abort, Response
import logging


class MjpegStream(Resource):
    """
    Real-time MJPEG stream from the microscope camera
    """

    def get(self):
        """
        Real-time MJPEG stream from the microscope camera
        """
        microscope = find_device("openflexure_microscope")
        # Restart stream worker thread
        microscope.camera.start_worker()

        return Response(
            gen(microscope.camera), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


class SnapshotStream(Resource):
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
        microscope = find_device("openflexure_microscope")
        # Restart stream worker thread
        microscope.camera.start_worker()

        return Response(microscope.camera.get_frame(), mimetype="image/jpeg")
