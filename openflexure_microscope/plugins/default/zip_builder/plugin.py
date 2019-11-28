from openflexure_microscope.devel import (
    MicroscopePlugin,
    MicroscopeViewPlugin,
    JsonResponse,
    request,
    jsonify,
    taskify,
)

from flask import send_file, abort

import uuid
import zipfile
import tempfile
import logging


class ZipBuilderAPIView(MicroscopeViewPlugin):
    def post(self):

        ids = list(JsonResponse(request).json)

        task = taskify(self.plugin.build_zip_from_capture_ids)(ids)

        # Return a handle on the autofocus task
        return jsonify(task.state), 201


class ZipListAPIView(MicroscopeViewPlugin):
    def get(self):
        return jsonify(list(self.plugin.session_zips.keys()))


class ZipGetterAPIView(MicroscopeViewPlugin):
    def get(self, session_id="No session ID"):
        logging.info(f"Session ID: {session_id}")

        return send_file(
            self.plugin.zip_from_id(session_id),
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"{session_id}.zip",
        )


class ZipBuilderPlugin(MicroscopePlugin):
    """
    ZIP-builder plugin
    """

    def __init__(self):
        super().__init__()

        self.session_zips = {}

        self.add_view("/get/<string:session_id>", ZipGetterAPIView)
        self.add_view("/get", ZipListAPIView)

        self.add_view("/build", ZipBuilderAPIView)

    def build_zip_from_capture_ids(self, capture_id_list):
        logging.debug(capture_id_list)

        fp = tempfile.NamedTemporaryFile(delete=False)

        with zipfile.ZipFile(fp, "w") as zipObj:
            for capture_id in capture_id_list:
                capture_obj = self.microscope.camera.image_from_id(capture_id)
                filePath = capture_obj.file
                zipObj.write(filePath)

        session_id = uuid.uuid4().hex
        self.session_zips[session_id] = fp

        return session_id

    def zip_from_id(self, session_id):
        fp = self.session_zips[session_id]
        fp.seek(0)
        return fp
