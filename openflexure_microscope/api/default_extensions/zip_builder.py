import logging
import os
import tempfile
import uuid
import zipfile
from typing import IO, List, Optional

from flask import abort, send_file, url_for
from labthings import fields, find_component, update_action_progress
from labthings.extensions import BaseExtension
from labthings.schema import Schema, pre_dump
from labthings.utilities import description_from_view
from labthings.views import ActionView, PropertyView, View, described_operation

from openflexure_microscope.captures import CaptureObject
from openflexure_microscope.microscope import Microscope


class ZipObjectSchema(Schema):
    id = fields.String()
    data_size = fields.Number()
    zip_size = fields.Number()
    links = fields.Dict()

    @pre_dump
    def generate_links(self, data, **_):
        data.links = {
            "download": {
                "href": url_for(
                    ZipGetterAPIView.endpoint, session_id=data.id, _external=True
                ),
                **description_from_view(ZipGetterAPIView),
            }
        }
        return data


class ZipObjectDescription:
    def __init__(
        self, id_: str, file_pointer: IO[bytes], data_size: Optional[float] = None
    ):
        self.id: str = id_
        self.fp: IO[bytes] = file_pointer
        self.data_size: Optional[float] = data_size
        self.zip_size: float = os.path.getsize(self.fp.name) * 1e-6

    def close(self):
        logging.debug(self.fp.name)
        self.fp.close()
        if os.path.exists(self.fp.name):
            os.unlink(self.fp.name)

        assert not os.path.exists(self.fp.name)

    def __del__(self):
        self.close()


class ZipManager:
    """
    ZIP-builder manager
    """

    def __init__(self):
        super().__init__()

        self.session_zips = {}

    def build_zip_from_capture_ids(
        self, microscope: Microscope, capture_id_list: List[str]
    ):
        logging.debug(capture_id_list)

        # Get array of captures from IDs
        optional_capture_list: List[Optional[CaptureObject]] = [
            microscope.captures.images.get(capture_id) for capture_id in capture_id_list
        ]
        # Remove Nones from list (missing/invalid captures)
        capture_list: List[CaptureObject] = [
            capture for capture in optional_capture_list if capture
        ]

        # Get size (in bytes) of each capture
        capture_sizes: List[float] = [
            os.path.getsize(capture_obj.file) for capture_obj in capture_list
        ]
        # Calculate size of input data in megabytes
        data_size_megabytes: float = sum(capture_sizes) * 1e-6

        # If more than 1GB
        if data_size_megabytes > 1000:
            # Throw exception
            raise Exception(
                "Zip data cannot exceed 1GB. Please transfer data manually."
            )

        # Number of files to add (used for task progress)
        n_files: int = len(capture_id_list)

        # Create temporary file
        fp: IO[bytes] = tempfile.NamedTemporaryFile(delete=False)

        # Open temp file as a ZIP file
        with zipfile.ZipFile(fp, "w") as zipObj:
            for index, capture_obj in enumerate(capture_list):
                # Add to ZIP file if it exists
                file_path = capture_obj.file
                rel_path = os.path.relpath(
                    file_path, microscope.captures.paths["default"]
                )
                zipObj.write(file_path, arcname=rel_path)
                # Update task progress
                update_action_progress(int((index / n_files) * 100))

        session_id: str = str(uuid.uuid4())
        session_description: ZipObjectDescription = ZipObjectDescription(
            session_id, fp, data_size=data_size_megabytes
        )
        self.session_zips[session_id] = session_description

        return self.session_zips[session_id]

    def marshaled_build_zip_from_capture_ids(self, *args, **kwargs):
        return ZipObjectSchema().dump(self.build_zip_from_capture_ids(*args, **kwargs))

    def zip_fp_from_id(self, session_id: str):
        return self.session_zips[session_id].fp

    def __del__(self):
        for zd in self.session_zips.values():
            zd.close()


class ZipBuilderExtension(BaseExtension):
    def __init__(self):
        super().__init__(
            "org.openflexure.zipbuilder",
            version="2.0.0",
            description="Build and download capture collections as ZIP files",
        )
        self.manager = ZipManager()

        self.add_view(ZipGetterAPIView, "/get/<string:session_id>", endpoint="get_id")
        self.add_view(ZipListAPIView, "/get", endpoint="get")
        self.add_view(ZipBuilderAPIView, "/build", endpoint="build")


class ZipBuilderAPIView(ActionView):
    args = fields.List(fields.String(), required=True)

    def post(self, args):
        """Build a zip file of some captures
        
        Given a list of capture IDs as its argument, this action will
        create a zip file that can be downloaded once the action has
        completed.
        """
        microscope = find_component("org.openflexure.microscope")

        # Build a zip file from the supplied IDs
        return self.extension.manager.marshaled_build_zip_from_capture_ids(
            microscope, args
        )


class ZipListAPIView(PropertyView):
    """List all the zip files currently available for download.
    """

    schema = ZipObjectSchema(many=True)

    def get(self):
        return self.extension.manager.session_zips.values()


class ZipGetterAPIView(View):
    """Download or delete a particular capture collection ZIP file
    """

    parameters = [
        {
            "name": "session_id",
            "in": "path",
            "description": "The unique ID of the zip builder session",
            "required": True,
            "schema": {"type": "string"},
        }
    ]
    responses = {404: {"description": "The session ID could not be found"}}

    @described_operation
    def get(self, session_id):
        """
        Download a particular capture collection ZIP file
        """
        if not session_id in self.extension.manager.session_zips:
            return abort(404)  # 404 Not Found

        logging.info("Retrieving zip (session ID: %s)", session_id)

        return send_file(
            self.extension.manager.zip_fp_from_id(session_id).name,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"{session_id}.zip",
        )

    get.responses = {
        200: {
            "content": {"application/zip": {}},
            "description": "A zip archive containing the selected captures",
        }
    }

    @described_operation
    def delete(self, session_id):
        """
        Close and delete a particular capture collection ZIP file
        """
        if not session_id in self.extension.manager.session_zips:
            return abort(404)  # 404 Not Found

        # Close the file
        self.extension.manager.session_zips[session_id].close()
        # Delete the file reference
        del self.extension.manager.session_zips[session_id]

        return {"return": session_id}

    delete.responses = {200: {"description": "The zip file was deleted"}}
