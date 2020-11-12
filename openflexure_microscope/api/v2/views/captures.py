from flask import abort, redirect, request, send_file, url_for
from labthings import Schema, fields, find_component
from labthings.marshalling import marshal_with, use_args
from labthings.utilities import description_from_view
from labthings.views import PropertyView, View
from marshmallow import pre_dump

from openflexure_microscope.api.utilities import get_bool


class InstrumentSchema(Schema):
    id = fields.UUID()
    configuration = fields.Dict()
    settings = fields.Dict()
    state = fields.Dict()


class ImageSchema(Schema):
    id = fields.UUID()
    time = fields.String(format="date")
    format = fields.String()
    name = fields.String()
    tags = fields.List(fields.String())
    annotations = fields.Dict()


class CaptureMetadataSchema(Schema):
    experimenter = fields.Dict()  # TODO: Make schema
    experimenterGroup = fields.Dict()  # TODO: Make schema
    dataset = fields.Dict()  # TODO: Make schema
    image = fields.Nested(ImageSchema())
    instrument = fields.Nested(InstrumentSchema())


class CaptureSchema(ImageSchema):
    """
    Schema containing only basic attributes required
    for interacting with a capture. Additional attributes
    are returned by using FullCaptureSchema 
    """

    dataset = fields.Dict()  # TODO: Make schema
    file = fields.String(
        data_key="path", description="Path of file on microscope device"
    )
    links = fields.Dict()

    @pre_dump
    def generate_links(self, data, **_):
        if isinstance(data, dict):
            capture_id = data.get("id")
            capture_name = data.get("name")
        else:
            capture_id = data.id
            capture_name = data.name

        links = {
            "self": {
                "href": url_for(CaptureView.endpoint, id_=capture_id, _external=True),
                "mimetype": "application/json",
                **description_from_view(CaptureView),
            },
            "tags": {
                "href": url_for(CaptureTags.endpoint, id_=capture_id, _external=True),
                "mimetype": "application/json",
                **description_from_view(CaptureTags),
            },
            "annotations": {
                "href": url_for(
                    CaptureAnnotations.endpoint, id_=capture_id, _external=True
                ),
                "mimetype": "application/json",
                **description_from_view(CaptureAnnotations),
            },
            "download": {
                "href": url_for(
                    CaptureDownload.endpoint,
                    id_=capture_id,
                    filename=capture_name,
                    _external=True,
                ),
                "mimetype": "image/jpeg",
                **description_from_view(CaptureDownload),
            },
        }

        if isinstance(data, dict):
            data["links"] = links
        else:
            data.links = links

        return data


class FullCaptureSchema(CaptureSchema):
    """
    Capture schema including metadata. We exclude this by default
    since it can become huge due to complex settings including
    lens shading tables and CSM matrices.
    """

    metadata = fields.Nested(CaptureMetadataSchema())


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

    @marshal_with(FullCaptureSchema())
    def get(self, id_):
        """
        Description of a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_obj

    def delete(self, id_):
        """
        Delete a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        # Delete the capture file
        capture_obj.delete()
        # Delete from capture list
        del microscope.captures.images[id_]

        return "", 204


class CaptureDownload(View):
    tags = ["captures"]
    responses = {200: {"content_type": "image/jpeg"}}

    def get(self, id_, filename):
        """
        Image data for a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        thumbnail = get_bool(request.args.get("thumbnail"))

        # If no filename is specified, redirect to the capture's currently set filename
        if not filename:
            return redirect(
                url_for(
                    "DownloadAPI",
                    id=id_,
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

    def get(self, id_):
        """
        Get tags associated with a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_obj.tags

    @use_args(fields.List(fields.String(), required=True))
    def put(self, args, id_):
        """
        Add tags to a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        capture_obj.put_tags(args)

        return capture_obj.tags

    @use_args(fields.List(fields.String(), required=True))
    def delete(self, args, id_):
        """
        Delete tags from a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        for tag in args:
            capture_obj.delete_tag(str(tag))

        return capture_obj.tags


class CaptureAnnotations(View):
    tags = ["captures"]

    def get(self, id_):
        """
        Get annotations associated with a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        return capture_obj.annotations

    @use_args(fields.Dict())
    def put(self, args, id_):
        """
        Update metadata for a single image capture
        """
        microscope = find_component("org.openflexure.microscope")
        capture_obj = microscope.captures.images.get(id_)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        capture_obj.put_annotations(args)

        return capture_obj.annotations
