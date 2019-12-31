from openflexure_microscope.api.utilities import get_bool, JsonResponse
from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.find import find_device
from openflexure_microscope.common.flask_labthings.decorators import use_args
from openflexure_microscope.common.flask_labthings import fields
from openflexure_microscope.utilities import filter_dict

from openflexure_microscope.api.v2.views.captures import capture_schema

import logging
from flask import jsonify, request, abort, url_for, redirect, send_file


class CaptureAPI(Resource):
    """
    Create a new image capture. 
    """

    @use_args(
        {
            "filename": fields.String(),
            "temporary": fields.Boolean(missing=False),
            "use_video_port": fields.Boolean(missing=False),
            "bayer": fields.Boolean(missing=False),
            "metadata": fields.Dict(missing={}),
            "tags": fields.List(fields.String, missing=[]),
            "resize": fields.Dict(missing=None),  # TODO: Validate keys
        }
    )
    def post(self, args):
        microscope = find_device("openflexure_microscope")

        resize = args.get("resize", None)
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
            output = microscope.camera.new_image(
                temporary=args.get("temporary"), filename=args.get("filename")
            )

            microscope.camera.capture(
                output.file,
                use_video_port=args.get("use_video_port"),
                resize=resize,
                bayer=args.get("bayer"),
            )

            # Inject system metadata
            output.put_metadata(microscope.metadata, system=True)

            # Insert custom metadata
            output.put_metadata(args.get("metadata"))

            # Insert custom tags
            output.put_tags(args.get("tags"))

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
