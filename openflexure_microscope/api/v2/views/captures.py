import logging
from flask import abort, request, redirect, url_for, send_file, jsonify

from openflexure_microscope.api.utilities import get_bool, JsonResponse

from openflexure_microscope.common.labthings.schema import Schema
from openflexure_microscope.common.labthings import fields
from openflexure_microscope.common.labthings.resource import Resource

from openflexure_microscope.common.labthings.find import find_device


class CaptureSchema(Schema):
    id = fields.String()
    file = fields.String(data_key="path")
    exists = fields.Bool(data_key="available")
    filename = fields.String()
    metadata = fields.Dict()

    # TODO: Add HTTP methods
    links = fields.Hyperlinks(
        {
            "self": {
                "href": fields.AbsoluteUrlFor("CaptureResource", id="<id>"),
                "mimetype": "application/json",
            },
            "tags": {
                "href": fields.AbsoluteUrlFor("CaptureTags", id="<id>"),
                "mimetype": "application/json",
            },
            "metadata": {
                "href": fields.AbsoluteUrlFor("CaptureMetadata", id="<id>"),
                "mimetype": "application/json",
            },
            "download": {
                "href": fields.AbsoluteUrlFor(
                    "CaptureDownload", id="<id>", filename="<filename>"
                ),
                "mimetype": "image/jpeg",
            },
        }
    )


capture_schema = CaptureSchema()
capture_list_schema = CaptureSchema(many=True)


class CaptureList(Resource):
    def get(self):
        microscope = find_device("openflexure_microscope")
        image_list = microscope.camera.images
        return capture_list_schema.jsonify(image_list)


class CaptureResource(Resource):
    def get(self, id):
        microscope = find_device("openflexure_microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_schema.jsonify(capture_obj)

    def delete(self, id):
        microscope = find_device("openflexure_microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        capture_obj.delete()

        return ("", 204)


class CaptureDownload(Resource):
    def get(self, id, filename):

        microscope = find_device("openflexure_microscope")
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


class CaptureTags(Resource):
    def get(self, id):

        microscope = find_device("openflexure_microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return jsonify(capture_obj.tags)

    def put(self, id):

        microscope = find_device("openflexure_microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        capture_obj.put_tags(data_dict)

        return jsonify(capture_obj.tags)

    def delete(self, capture_id):

        microscope = find_device("openflexure_microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        for tag in data_dict:
            capture_obj.delete_tag(str(tag))

        return jsonify(capture_obj.tags)


class CaptureMetadata(Resource):
    def get(self, id):
        microscope = find_device("openflexure_microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return jsonify(capture_obj.metadata)

    def put(self, id):
        microscope = find_device("openflexure_microscope")
        capture_obj = microscope.camera.image_from_id(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        # TODO: Allow putting system metadata maybe?
        capture_obj.put_metadata(data_dict)

        return jsonify(capture_obj.metadata)


def add_captures_to_labthing(labthing, prefix=""):
    """
    Add all capture resources to a labthing
    """
    labthing.add_resource(CaptureList, f"{prefix}/captures", endpoint="CaptureList")
    labthing.register_property(CaptureList)
    labthing.add_resource(
        CaptureResource, f"{prefix}/captures/<id>", endpoint="CaptureResource"
    )
    labthing.add_resource(
        CaptureDownload,
        f"{prefix}/captures/<id>/download/<filename>",
        endpoint="CaptureDownload",
    )
    labthing.add_resource(
        CaptureTags, f"{prefix}/captures/<id>/tags", endpoint="CaptureTags"
    )
    labthing.add_resource(
        CaptureMetadata, f"{prefix}/captures/<id>/metadata", endpoint="CaptureMetadata"
    )
