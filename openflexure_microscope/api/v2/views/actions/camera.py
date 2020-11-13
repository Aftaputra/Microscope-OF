import io
import logging

from flask import send_file
from labthings import Schema, fields, find_component
from labthings.views import ActionView

from openflexure_microscope.api.v2.views.captures import CaptureSchema


class CaptureResizeSchema(Schema):
    width = fields.Integer(example=640, required=True)
    height = fields.Integer(example=480, required=True)


class BasicCaptureArgs(Schema):
    use_video_port = fields.Boolean(missing=False)
    bayer = fields.Boolean(
        missing=False, description="Include raw bayer data in capture"
    )
    resize = fields.Nested(CaptureResizeSchema(), required=False)


class FullCaptureArgs(BasicCaptureArgs):
    filename = fields.String(example="MyFileName")
    temporary = fields.Boolean(missing=False, description="Delete capture on shutdown")
    annotations = fields.Dict(missing={}, example={"Client": "SwaggerUI"})
    tags = fields.List(fields.String, missing=[], example=["docs"])


class CaptureAPI(ActionView):
    """
    Create a new image capture. 
    """

    args = FullCaptureArgs()
    schema = CaptureSchema()

    def post(self, args):
        """
        Create a new capture
        """
        microscope = find_component("org.openflexure.microscope")

        resize = args.get("resize", None)
        if resize:
            resize = (
                int(resize["width"]),
                int(resize["height"]),
            )  # Convert dict to tuple

        # Explicitally acquire lock (prevents empty files being created if lock is unavailable)
        with microscope.camera.lock:
            return microscope.capture(
                filename=args.get("filename"),
                temporary=args.get("temporary"),
                use_video_port=args.get("use_video_port"),
                resize=resize,
                bayer=args.get("bayer"),
                annotations=args.get("annotations"),
                tags=args.get("tags"),
            )


class RAMCaptureAPI(ActionView):
    """
    Take a non-persistant image capture.
    """

    args = BasicCaptureArgs()
    responses = {200: {"content_type": "image/jpeg"}}

    def post(self, args):
        """
        Take a non-persistant image capture.
        """
        microscope = find_component("org.openflexure.microscope")

        resize = args.get("resize", None)
        if resize:
            resize = (
                int(resize["width"]),
                int(resize["height"]),
            )  # Convert dict to tuple

        # Open a BytesIO stream to be destroyed once request has returned
        with microscope.camera.lock, io.BytesIO() as stream:

            microscope.camera.capture(
                stream,
                use_video_port=args.get("use_video_port"),
                resize=resize,
                bayer=args.get("bayer"),
            )

            stream.seek(0)

            return send_file(io.BytesIO(stream.getbuffer()), mimetype="image/jpeg")


class GPUPreviewStartAPI(ActionView):
    """
    Start the onboard GPU preview.
    Optional "window" parameter can be passed to control the position and size of the preview window,
    in the format ``[x, y, width, height]``.
    """

    args = {"window": fields.List(fields.Integer, missing=[], example=[0, 0, 640, 480])}

    def post(self, args):
        """
        Start the onboard GPU preview.
        """
        microscope = find_component("org.openflexure.microscope")

        window = args.get("window")
        logging.debug(window)

        if len(window) != 4:
            fullscreen = True
            window = None
        else:
            fullscreen = False
            window = [int(w) for w in window]

        microscope.camera.start_preview(fullscreen=fullscreen, window=window)
        return microscope.state


class GPUPreviewStopAPI(ActionView):
    def post(self):
        """
        Stop the onboard GPU preview.
        """
        microscope = find_component("org.openflexure.microscope")
        microscope.camera.stop_preview()
        return microscope.state
