from openflexure_microscope.api.utilities import get_bool, JsonResponse
from openflexure_microscope.api.views import MicroscopeView
from openflexure_microscope.utilities import filter_dict

import logging
from flask import jsonify, request, abort, url_for, redirect, send_file


class CaptureAPI(MicroscopeView):
    def post(self):
        """
        Create a new image capture.

        .. :quickref: Actions; New capture

        **Example request**:

        .. sourcecode:: http

          POST /actions/camera/capture HTTP/1.1
          Accept: application/json

          {
            "filename": "myfirstcapture",
            "temporary": false,
            "use_video_port": true,
            "bayer": true,
            "size": {
                "width": 640,
                "height": 480
            }
          }

        :>header Accept: application/json

        :<json string filename: filename of stored capture
        :<json boolean temporary: delete the capture file on microscope after closing
        :<json boolean use_video_port: capture still image from the video port
        :<json boolean bayer: keep raw capture data in the image file
        :<json json size:   - **x** *(int)*: x-axis resize
                            - **y** *(int)*: y-axis resize

        :>json boolean available: availability of capture data
        :>json string filename: filename of capture
        :>json string id: unique id of the capture object
        :>json boolean temporary: delete the capture file on microscope after closing
        :>json boolean locked: file locked for modifications (mostly used for video recording)
        :>json string path: path on pi storage to the capture file, if available
        :>json boolean stream: capture stored in-memory as a BytesIO stream
        :>json json uri: - **download** *(string)*: api uri to the capture file download
                         - **state** *(string)*: api uri to the capture json representation

        :<header Content-Type: application/json
        :status 200: capture created
        """
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
        with self.microscope.camera.lock:
            output = self.microscope.camera.new_image(
                temporary=temporary, filename=filename
            )

            self.microscope.camera.capture(
                output.file, use_video_port=use_video_port, resize=resize, bayer=bayer
            )

            # Inject system metadata
            system_metadata = {
                "microscope_settings": self.microscope.read_settings(),
                "microscope_state": self.microscope.state,
                "microscope_id": self.microscope.id,
                "microscope_name": self.microscope.name,
            }
            output.system_metadata.update(system_metadata)

            # Insert custom metadata
            output.put_metadata(metadata)

            # Insert custom tags
            output.put_tags(tags)

        return jsonify(output.state)


class GPUPreviewStartAPI(MicroscopeView):
    def post(self, operation):
        """
        Start the onboard GPU preview.
        Optional "window" parameter can be passed to control the position and size of the preview window,
        in the format ``[x, y, width, height]``.

        .. :quickref: Actions; Start on-board preview

        **Example requests**:

        .. sourcecode:: http

          POST /actions/camera/preview/start HTTP/1.1
          Accept: application/json

          {
            "window": [0, 0, 480, 320],
          }

        :>header Accept: application/json

        :<header Content-Type: application/json
        :status 200: preview started/stopped
        """
        payload = JsonResponse(request)

        window = payload.param("window", default=[])
        logging.debug(window)

        if len(window) != 4:
            fullscreen = True
            window = None
        else:
            fullscreen = False
            window = [int(w) for w in window]

        self.microscope.camera.start_preview(fullscreen=fullscreen, window=window)

        return jsonify(self.microscope.state)


class GPUPreviewStopAPI(MicroscopeView):
    def post(self, operation):
        """
        Stop the onboard GPU preview.

        .. :quickref: Actions; Stop on-board preview

        **Example requests**:

        .. sourcecode:: http

          POST /actions/camera/preview/stop HTTP/1.1
          Accept: application/json

        :>header Accept: application/json

        :<header Content-Type: application/json
        :status 200: preview started/stopped
        """

        self.microscope.camera.stop_preview()
        return jsonify(self.microscope.state)
