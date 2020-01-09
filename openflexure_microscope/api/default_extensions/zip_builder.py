from openflexure_microscope.devel import (
    JsonResponse,
    request,
    jsonify,
    taskify,
    update_task_progress,
)

from flask import send_file, abort

import uuid
import os
import zipfile
import tempfile
import logging

from openflexure_microscope.common.flask_labthings.find import find_device
from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.extensions import BaseExtension


class ZipManager:
    """
    ZIP-builder manager
    """

    def __init__(self):
        super().__init__()

        self.session_zips = {}

    def build_zip_from_capture_ids(self, microscope, capture_id_list):
        logging.debug(capture_id_list)

        # Get array of captures from IDs
        capture_list = [
            microscope.camera.image_from_id(capture_id)
            for capture_id in capture_id_list
        ]
        # Remove Nones from list (missing/invalid captures)
        capture_list = [capture for capture in capture_list if capture]

        # Get size (in bytes) of each capture
        capture_sizes = [
            os.path.getsize(capture_obj.file) for capture_obj in capture_list
        ]
        # Calculate size of input data in megabytes
        data_size_megabytes = sum(capture_sizes) * 1e-6

        # If more than 1GB
        if data_size_megabytes > 1000:
            # Throw exception
            raise Exception(
                "Zip data cannot exceed 1GB. Please transfer data manually."
            )

        # Number of files to add (used for task progress)
        n_files = len(capture_id_list)

        # Create temporary file
        fp = tempfile.NamedTemporaryFile(delete=False)

        # Open temp file as a ZIP file
        with zipfile.ZipFile(fp, "w") as zipObj:
            for index, capture_obj in enumerate(capture_list):
                # Add to ZIP file if it exists
                file_path = capture_obj.file
                rel_path = os.path.relpath(
                    file_path, microscope.camera.paths["default"]
                )
                zipObj.write(file_path, arcname=rel_path)
                # Update task progress
                update_task_progress(int((index / n_files) * 100))

        session_id = uuid.uuid4()
        # self.session_zips[session_id] = fp
        self.session_zips[session_id] = {
            "id": session_id,
            "fp": fp,
            "data_size": data_size_megabytes,
            "zip_size": os.path.getsize(fp.name) * 1e-6,
        }

        return self.session_zips[session_id]

    def zip_from_id(self, session_id):
        return self.session_zips[session_id]["fp"]


# Create a global ZIP manager
default_zip_manager = ZipManager()


class ZipBuilderAPIView(Resource):
    def post(self):

        ids = list(JsonResponse(request).json)
        microscope = find_device("org.openflexure.microscope")

        task = taskify(default_zip_manager.build_zip_from_capture_ids)(microscope, ids)

        # Return a handle on the autofocus task
        return jsonify(task.state), 201


class ZipListAPIView(Resource):
    def get(self):
        return jsonify(default_zip_manager.session_zips)


class ZipGetterAPIView(Resource):
    def get(self, session_id):
        if not session_id in default_zip_manager.session_zips:
            return abort(404)  # 404 Not Found

        logging.info(f"Session ID: {session_id}")

        return send_file(
            default_zip_manager.zip_from_id(session_id).name,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"{session_id}.zip",
        )

    def delete(self, session_id):
        if not session_id in default_zip_manager.session_zips:
            return abort(404)  # 404 Not Found

        logging.info(f"Session ID: {session_id}")

        fp = default_zip_manager.zip_from_id(session_id)
        logging.debug(fp.name)
        fp.close()
        os.unlink(fp.name)

        assert not os.path.exists(fp.name)

        del default_zip_manager.session_zips[session_id]

        return jsonify({"return": session_id})


zip_extension_v2 = BaseExtension("zip_builder")

zip_extension_v2.add_view(ZipGetterAPIView, "/get/<string:session_id>")
zip_extension_v2.add_view(ZipListAPIView, "/get")

zip_extension_v2.add_view(ZipBuilderAPIView, "/build")
zip_extension_v2.register_action(ZipBuilderAPIView)
