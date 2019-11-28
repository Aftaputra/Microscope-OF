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
import os
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
    def get(self, session_id):
        if not session_id in self.plugin.session_zips:
            return abort(404)  # 404 Not Found

        logging.info(f"Session ID: {session_id}")

        return send_file(
            self.plugin.session_zips[session_id].name,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"{session_id}.zip",
        )

    def delete(self, session_id):
        if not session_id in self.plugin.session_zips:
            return abort(404)  # 404 Not Found

        logging.info(f"Session ID: {session_id}")
        logging.debug(self.plugin.session_zips[session_id].name)

        fp = self.plugin.session_zips[session_id]
        fp.close()
        os.unlink(fp.name)

        assert not os.path.exists(fp.name)

        del self.plugin.session_zips[session_id]

        return jsonify({"return": session_id})


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
        return self.session_zips[session_id]
