from openflexure_microscope.api.utilities import gen, JsonResponse

from labthings import find_component
from labthings.utilities import get_by_path, set_by_path, create_from_path
from labthings.views import View, PropertyView

from flask import Response


class MjpegStream(PropertyView):
    """
    Real-time MJPEG stream from the microscope camera
    """
    responses = {
        200: {
            "content_type": "multipart/x-mixed-replace"
        }
    }

    def get(self):
        """
        MJPEG stream from the microscope camera.

        Note: While the code actually getting frame data from a camera and storing it in
        camera.frame runs in a thread, the gen(microscope.camera) generator does not.
        This response is therefore blocking. The generator just yields the most recent
        frame from the camera object, passed to the Flask response, and then repeats until
        the connection is closed.

        Without monkey patching, or using a native threaded server, the stream
        will block all proceeding requests.
        """
        microscope = find_component("org.openflexure.microscope")
        # Restart stream worker thread
        microscope.camera.start_worker()

        return Response(
            gen(microscope.camera), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


class SnapshotStream(PropertyView):
    """
    Single JPEG snapshot from the camera stream
    """

    responses = {
        200: {
            "content_type": "image/jpeg",
            "description": "Snapshot taken"
        }
    }

    def get(self):
        """
        Single snapshot from the camera stream
        """
        microscope = find_component("org.openflexure.microscope")
        # Restart stream worker thread
        microscope.camera.start_worker()

        return Response(microscope.camera.get_frame(), mimetype="image/jpeg")
