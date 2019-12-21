from openflexure_microscope.api.utilities import get_bool, JsonResponse
from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.find import find_device
from openflexure_microscope.utilities import filter_dict

from openflexure_microscope.api.v2.views.captures import capture_schema

import logging
from flask import jsonify, request, abort, url_for, redirect, send_file


class CaptureAPI(Resource):
    """
    Create a new image capture. 
    """

    def post(self):
        microscope = find_device("openflexure_microscope")
        payload = JsonResponse(request)

        filename = payload.param("filename")
        temporary = payload.param("temporary", default=False, convert=bool)
        use_video_port = payload.param("use_video_port", default=False, convert=bool)
        bayer = payload.param("bayer", default=True, convert=bool)
        metadata = payload.param("metadata", default={}, convert=dict)
        tags = payload.param("tags", default=[], convert=list)

        resize = payload.param("size", default=None)
        if resize:
            if ("width" in resize) and ("height" in resize):
                resize = (
                    int(resize["width"]),
                    int(resize["height"]),
                )  # Convert dict to tuple
            else:
                abort(404)

        # Explicitally acquire lock (prevents empty files being created if lock is unavailable)
        with microscope.camera.lock:
            output = microscope.camera.new_image(temporary=temporary, filename=filename)

            microscope.camera.capture(
                output.file, use_video_port=use_video_port, resize=resize, bayer=bayer
            )

            # Inject system metadata
            output.put_metadata(microscope.metadata, system=True)

            # Insert custom metadata
            output.put_metadata(metadata)

            # Insert custom tags
            output.put_tags(tags)

        return capture_schema.jsonify(output)


class GPUPreviewStartAPI(Resource):
    """
    Start the onboard GPU preview.
    Optional "window" parameter can be passed to control the position and size of the preview window,
    in the format ``[x, y, width, height]``.
    """

    def post(self):
        microscope = find_device("openflexure_microscope")
        payload = JsonResponse(request)

        window = payload.param("window", default=[])
        logging.debug(window)

        if len(window) != 4:
            fullscreen = True
            window = None
        else:
            fullscreen = False
            window = [int(w) for w in window]

        microscope.camera.start_preview(fullscreen=fullscreen, window=window)

        return jsonify(microscope.state)


class GPUPreviewStopAPI(Resource):
    """
    Start the onboard GPU preview.
    """

    def post(self):
        microscope = find_device("openflexure_microscope")
        microscope.camera.stop_preview()
        return jsonify(microscope.state)
