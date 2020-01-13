from openflexure_microscope.api.utilities import gen, JsonResponse

from openflexure_microscope.common.labthings_core.utilities import (
    get_by_path,
    set_by_path,
    create_from_path,
)

from openflexure_microscope.common.flask_labthings.find import find_component
from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.decorators import doc_response, ThingProperty

from flask import Response

@ThingProperty
class MjpegStream(Resource):
    """
    Real-time MJPEG stream from the microscope camera
    """

    @doc_response(200, mimetype="multipart/x-mixed-replace")
    def get(self):
        """
        MJPEG stream from the microscope camera
        """
        microscope = find_component("org.openflexure.microscope")
        # Restart stream worker thread
        microscope.camera.start_worker()

        return Response(
            gen(microscope.camera), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


@ThingProperty
class SnapshotStream(Resource):
    """
    Single JPEG snapshot from the camera stream
    """

    @doc_response(200, description="Snapshot taken", mimetype="image/jpeg")
    def get(self):
        """
        Single snapshot from the camera stream
        """
        microscope = find_component("org.openflexure.microscope")
        # Restart stream worker thread
        microscope.camera.start_worker()

        return Response(microscope.camera.get_frame(), mimetype="image/jpeg")
