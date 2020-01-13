import logging
from flask import abort, request, redirect, url_for, send_file, jsonify

from openflexure_microscope.api.utilities import get_bool, JsonResponse

from openflexure_microscope.common.flask_labthings.schema import Schema
from openflexure_microscope.common.flask_labthings import fields
from openflexure_microscope.common.flask_labthings.resource import Resource
from openflexure_microscope.common.flask_labthings.utilities import (
    description_from_view,
)
from openflexure_microscope.common.flask_labthings.decorators import marshal_with, doc_response, Tag, ThingProperty

from openflexure_microscope.common.flask_labthings.find import find_component

from marshmallow import pre_dump


class CaptureSchema(Schema):
    id = fields.String()
    file = fields.String(
        data_key="path", description="Path of file on microscope device"
    )
    exists = fields.Bool(data_key="available")
    filename = fields.String()
    metadata = fields.Dict()

    links = fields.Dict()

    # TODO: Automate this somewhat
    @pre_dump
    def generate_links(self, data, **kwargs):
        data.links = {
            "self": {
                "href": url_for(CaptureResource.endpoint, id=data.id, _external=True),
                "mimetype": "application/json",
                **description_from_view(CaptureResource),
            },
            "tags": {
                "href": url_for(CaptureTags.endpoint, id=data.id, _external=True),
                "mimetype": "application/json",
                **description_from_view(CaptureTags),
            },
            "metadata": {
                "href": url_for(CaptureMetadata.endpoint, id=data.id, _external=True),
                "mimetype": "application/json",
                **description_from_view(CaptureMetadata),
            },
            "download": {
                "href": url_for(
                    CaptureDownload.endpoint,
                    id=data.id,
                    filename=data.filename,
                    _external=True,
                ),
                "mimetype": "image/jpeg",
                **description_from_view(CaptureDownload),
            },
        }
        return data


capture_schema = CaptureSchema()
capture_list_schema = CaptureSchema(many=True)


@ThingProperty
@Tag("captures")
class CaptureList(Resource):
    @marshal_with(CaptureSchema(many=True))
    def get(self):
        """
        List all image captures
        """
        microscope = find_component("org.openflexure.microscope")
        image_list = microscope.camera.images
        return image_list


@Tag("captures")
class CaptureResource(Resource):
    @marshal_with(CaptureSchema())
    def get(self, id):
        """
        Description of a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_obj

    def delete(self, id):
        """
        Delete a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        capture_obj.delete()

        return "", 204


@Tag("captures")
class CaptureDownload(Resource):
    @doc_response(200, mimetype="image/jpeg")
    def get(self, id, filename):
        """
        Image data for a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        thumbnail = get_bool(request.args.get("thumbnail"))

        # If no filename is specified, redirect to the capture's currently set filename
        if not filename:
            return redirect(
                url_for(
                    "DownloadAPI",
                    id=id,
                    filename=capture_obj.filename,
                    thumbnail=thumbnail,
                ),
                code=307,
            )

        # Download the image data using the requested filename
        if thumbnail:
            img = capture_obj.thumbnail
        else:
            img = capture_obj.data

        return send_file(img, mimetype="image/jpeg")


@Tag("captures")
class CaptureTags(Resource):
    def get(self, id):
        """
        Get tags associated with a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return jsonify(capture_obj.tags)

    def put(self, id):
        """
        Add tags to a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        # TODO: Replace with normal Flask request JSON thing
        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        capture_obj.put_tags(data_dict)

        return jsonify(capture_obj.tags)

    def delete(self, capture_id):
        """
        Delete tags from a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        for tag in data_dict:
            capture_obj.delete_tag(str(tag))

        return jsonify(capture_obj.tags)


@Tag("captures")
class CaptureMetadata(Resource):
    def get(self, id):
        """
        Get metadata associated with a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return jsonify(capture_obj.metadata)

    def put(self, id):
        """
        Update metadata for a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        # TODO: Allow putting system metadata maybe?
        capture_obj.put_metadata(data_dict)

        return jsonify(capture_obj.metadata)
