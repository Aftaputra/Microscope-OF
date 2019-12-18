from openflexure_microscope.api.utilities import gen, JsonResponse
from openflexure_microscope.utilities import get_by_path, set_by_path, create_from_path

from openflexure_microscope.common.labthings.find import find_device
from openflexure_microscope.common.labthings.resource import Resource

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


def add_streams_to_labthing(labthing, prefix=""):
    """
    Add all stream resources to a labthing
    """
    labthing.add_resource(
        MjpegStream, f"{prefix}/streams/mjpeg", endpoint="MjpegStream"
    )
    labthing.register_property(MjpegStream)
    labthing.add_resource(
        SnapshotStream, f"{prefix}/streams/snapshot", endpoint="SnapshotStream"
    )
    labthing.register_property(SnapshotStream)
