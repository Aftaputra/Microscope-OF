import logging

from flask import abort, redirect, request, send_file, url_for
from labthings import Schema, fields, find_component
from labthings.marshalling import marshal_with
from labthings.utilities import description_from_view
from labthings.views import PropertyView, View
from marshmallow import pre_dump

from openflexure_microscope.api.utilities import JsonResponse, get_bool


class InstrumentSchema(Schema):
    id = fields.UUID()
    configuration = fields.Dict()
    settings = fields.Dict()
    state = fields.Dict()


class CaptureMetadataImageSchema(Schema):
    id = fields.UUID()
    acquisitionDate = fields.String(format="date")
    format = fields.String()
    name = fields.String()
    tags = fields.List(fields.String())
    annotations = fields.Dict()


class CaptureMetadataSchema(Schema):
    experimenter = fields.Dict()  # TODO: Make schema
    experimenterGroup = fields.Dict()  # TODO: Make schema
    dataset = fields.Dict()  # TODO: Make schema
    image = fields.Nested(CaptureMetadataImageSchema())
    instrument = fields.Nested(InstrumentSchema())


class CaptureSchema(Schema):
    id = fields.String()
    file = fields.String(
        data_key="path", description="Path of file on microscope device"
    )
    exists = fields.Bool(data_key="available")
    name = fields.String()
    metadata = fields.Nested(CaptureMetadataSchema())

    links = fields.Dict()

    # TODO: Automate this somewhat
    @pre_dump
    def generate_links(self, data, **kwargs):
        data.links = {
            "self": {
                "href": url_for(CaptureView.endpoint, id=data.id, _external=True),
                "mimetype": "application/json",
                **description_from_view(CaptureView),
            },
            "tags": {
                "href": url_for(CaptureTags.endpoint, id=data.id, _external=True),
                "mimetype": "application/json",
                **description_from_view(CaptureTags),
            },
            "annotations": {
                "href": url_for(
                    CaptureAnnotations.endpoint, id=data.id, _external=True
                ),
                "mimetype": "application/json",
                **description_from_view(CaptureAnnotations),
            },
            "download": {
                "href": url_for(
                    CaptureDownload.endpoint,
                    id=data.id,
                    filename=data.name,
                    _external=True,
                ),
                "mimetype": "image/jpeg",
                **description_from_view(CaptureDownload),
            },
        }
        return data


class CaptureList(PropertyView):
    tags = ["captures"]
    schema = CaptureSchema(many=True)

    def get(self):
        """
        List all image captures
        """
        microscope = find_component("org.openflexure.microscope")
        image_list = microscope.captures.images.values()
        return image_list


class CaptureView(View):
    tags = ["captures"]

    @marshal_with(CaptureSchema())
    def get(self, id):
        """
        Description of a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_obj

    def delete(self, id):
        """
        Delete a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        # Delete the capture file
        capture_obj.delete()
        # Delete from capture list
        del microscope.captures.images[id]

        return "", 204


class CaptureDownload(View):
    tags = ["captures"]
    responses = {200: {"content_type": "image/jpeg"}}

    def get(self, id, filename):
        """
        Image data for a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

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


class CaptureTags(View):
    tags = ["captures"]

    def get(self, id):
        """
        Get tags associated with a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_obj.tags

    def put(self, id):
        """
        Add tags to a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        # TODO: Replace with normal Flask request JSON thing
        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        capture_obj.put_tags(data_dict)

        return capture_obj.tags

    def delete(self, id):
        """
        Delete tags from a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        for tag in data_dict:
            capture_obj.delete_tag(str(tag))

        return capture_obj.tags


class CaptureAnnotations(View):
    tags = ["captures"]

    def get(self, id):
        """
        Get annotations associated with a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_obj.annotations

    def put(self, id):
        """
        Update metadata for a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json
        logging.debug(data_dict)

        if type(data_dict) != dict:
            return abort(400)

        capture_obj.put_annotations(data_dict)

        return capture_obj.annotations
