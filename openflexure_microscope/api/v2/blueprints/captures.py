"""
Top-level representation of all acquired captures
"""

from openflexure_microscope.api.utilities import get_bool, JsonResponse
from openflexure_microscope.api.views import MicroscopeView
from openflexure_microscope.utilities import filter_dict
from openflexure_microscope.api.utilities import blueprint_for_module

from flask import jsonify, request, abort, url_for, redirect, send_file, Blueprint


def captures_representation(capture_list: list, include_unavailable: bool = False):
    """
    Generate a dictionary representation of all captures, including Flask route URLs

    Args:
        capture_list (list): List of capture objects
        include_unavailable (bool): Include unavailable captures in response?

    Returns:
        dict: Dictionary representation of all captures

    """
    if include_unavailable:
        captures = {image.id: image.state for image in capture_list}
    else:
        captures = {
            image.id: image.state for image in capture_list if image.state["available"]
        }

    for capture_key, capture_repr in captures.items():
        # Add API routes to returned representations
        extra_state = {
            "links": {
                "self": "{}".format(url_for(".capture", capture_id=capture_key)),
                "download": "{}".format(
                    url_for(
                        ".capture_download",
                        capture_id=capture_key,
                        filename=capture_repr["filename"],
                    )
                ),
                "tags": "{}".format(url_for(".capture_tags", capture_id=capture_key)),
            }
        }

        captures[capture_key].update(extra_state)

    return captures


class ListAPI(MicroscopeView):
    def get(self):
        """
        Get list of image captures.

        .. :quickref: Captures; Get collection of captures

        :>header Accept: application/json
        :query include_unavailable: return json representations of captures that have been completely deleted

        :>jsonarr boolean available: availability of capture data
        :>jsonarr string filename: filename of capture
        :>jsonarr string id: unique id of the capture object
        :>jsonarr boolean keep_on_disk: keep the capture file on microscope after closing
        :>jsonarr boolean locked: file locked for modifications (mostly used for video recording)
        :>jsonarr string path: path on pi storage to the capture file, if available
        :>jsonarr boolean stream: capture stored in-memory as a BytesIO stream
        :>jsonarr json uri: - **download** *(string)*: api uri to the capture file download
                            - **state** *(string)*: api uri to the capture json representation

        :>header Content-Type: application/json
        :status 200: capture found
        :status 404: no capture found with that id
        """
        representation = captures_representation(self.microscope.camera.images)

        return jsonify(representation)

    def delete(self):
        """
        Delete all captures

        .. :quickref: Captures; Delete all captures
        """
        for image in self.microscope.camera.images:
            image.delete()

        captures = [image.state for image in self.microscope.camera.images]

        return jsonify(captures)


class CaptureAPI(MicroscopeView):
    def get(self, capture_id):
        """
        Get JSON representation of a capture

        .. :quickref: Capture; Get capture

        **Example request**:

        .. sourcecode:: http

          GET /camera/capture/d0b2067abbb946f19351e075c5e7cd5b/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
              "available": true, 
              "bytestream": false, 
              "keep_on_disk": false, 
              "locked": false, 
              "metadata": {
                  "filename": "2018-11-16_10-21-53.jpeg", 
                  "id": "d0b2067abbb946f19351e075c5e7cd5b", 
                  "path": "capture/2018-11-16_10-21-53.jpeg", 
                  "time": "2018-11-16_10-21-53"
              }
              "uri": {
                  "download": "/api/v1/capture/d0b2067abbb946f19351e075c5e7cd5b/download", 
                  "state": "/api/v1/capture/d0b2067abbb946f19351e075c5e7cd5b/"
              }
          }

        :>json boolean available: availability of capture data
        :>json string filename: filename of capture
        :>json string id: unique id of the capture object
        :>json boolean keep_on_disk: keep the capture file on microscope after closing
        :>json boolean locked: file locked for modifications (mostly used for video recording)
        :>json string path: path on pi storage to the capture file, if available
        :>json boolean stream: capture stored in-memory as a BytesIO stream
        :>json json uri: - **download** *(string)*: api uri to the capture file download
                         - **state** *(string)*: api uri to the capture json representation

        """

        try:
            representation = captures_representation(self.microscope.camera.images)[
                capture_id
            ]
        except KeyError:
            return abort(404)  # 404 Not Found

        return jsonify(representation)

    def delete(self, capture_id):
        """
        Delete all capture data from the Pi, even if `keep_on_disk=true;`.

        .. :quickref: Capture; Delete capture.
        """
        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        capture_obj.delete()

        return jsonify({"return": capture_id})

    def put(self, capture_id):
        """
        Add arbitrary metadata to the capture

        .. :quickref: Capture; Update capture metadata

        **Example request**:

        .. sourcecode:: http

          PUT /camera/capture/d0b2067abbb946f19351e075c5e7cd5b HTTP/1.1
          Accept: application/json

          {
            "user_id": "ofm_1234", 
            "patient_number": 1452, 
          }

        :>header Accept: application/json

        :<header Content-Type: application/json
        :status 200: metadata updated
        """

        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        capture_obj.put_metadata(data_dict)

        capture_metadata = capture_obj.state

        return jsonify(capture_metadata)


class DownloadRedirectAPI(MicroscopeView):
    def get(self, capture_id):
        """
        Return image data for a capture.

        Return capture data as an image file with the requested filename. 
        I.e., `/(capture_id)/download/foo.jpeg` will download the image as 
        `foo.jpeg`, regardless of the capture's initially set filename.

        Route automatically redirects to download the capture under it's currently set filename. 
        I.e., `/(capture_id)/download` will 
        redirect to `/(capture_id)/download/(filename)`.

        .. :quickref: Capture; Download capture image

        **Example request**:

        .. sourcecode:: http

          GET /camera/capture/d0b2067abbb946f19351e075c5e7cd5b/download/2018-11-20_16-04-17.jpeg HTTP/1.1
          Accept: image/jpeg

        :>header Accept: image/jpeg
        :query thumbnail: return an image thumbnail e.g. ?thumbnail=true

        :>header Content-Type: image/jpeg
        :status 200: capture data found
        :status 404: no capture found with that id

        """
        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj or not capture_obj.state["available"]:
            return abort(404)  # 404 Not Found

        thumbnail = get_bool(request.args.get("thumbnail"))

        return redirect(
            url_for(
                ".capture_download",
                capture_id=capture_id,
                filename=capture_obj.filename,
                thumbnail=thumbnail,
            ),
            code=307,
        )


class DownloadAPI(MicroscopeView):
    def get(self, capture_id, filename):

        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj or not capture_obj.state["available"]:
            return abort(404)  # 404 Not Found

        thumbnail = get_bool(request.args.get("thumbnail"))

        # If no filename is specified, redirect to the capture's currently set filename
        if not filename:
            return redirect(
                url_for(
                    "capture_download",
                    capture_id=capture_id,
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


class TagsAPI(MicroscopeView):
    def get(self, capture_id):
        """
        Return tag list for a capture.

        .. :quickref: Capture; Show capture tags

        **Example request**:

        .. sourcecode:: http

          GET /camera/capture/d0b2067abbb946f19351e075c5e7cd5b/tags HTTP/1.1
          Accept: text/json

        :>header Accept: text/json

        :>header Content-Type: text/json
        :status 200: capture data found
        :status 404: no capture found with that id
        """
        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj or not capture_obj.state["available"]:
            return abort(404)  # 404 Not Found

        return jsonify(capture_obj.tags)

    def put(self, capture_id):
        """
        Add tags to the capture

        .. :quickref: Capture; Update capture tags

        **Example request**:

        .. sourcecode:: http

          PUT /camera/capture/d0b2067abbb946f19351e075c5e7cd5b/tags HTTP/1.1
          Accept: application/json

          ["tests", "mytag", "someothertag"]

        :>header Accept: application/json

        :<header Content-Type: application/json
        :status 200: metadata updated
        """

        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj or not capture_obj.state["available"]:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        capture_obj.put_tags(data_dict)

        return jsonify(capture_obj.tags)

    def delete(self, capture_id):
        """
        Delete tags from the capture

        .. :quickref: Capture; Delete tags.

        **Example request**:

        .. sourcecode:: http

          DELETE /camera/capture/d0b2067abbb946f19351e075c5e7cd5b/tags HTTP/1.1
          Accept: application/json

          ["tests", "mytag"]

        :>header Accept: application/json

        :<header Content-Type: application/json
        :status 200: metadata updated
        """
        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        data_dict = JsonResponse(request).json

        if type(data_dict) != list:
            return abort(400)

        for tag in data_dict:
            capture_obj.delete_tag(str(tag))

        return jsonify(capture_obj.tags)


def construct_blueprint(microscope_obj):
    
    blueprint = blueprint_for_module(__name__)

    # Tag routes
    blueprint.add_url_rule(
        "/<capture_id>/tags",
        view_func=TagsAPI.as_view("capture_tags", microscope=microscope_obj),
    )

    # Capture routes
    blueprint.add_url_rule(
        "/<capture_id>/download/<filename>",
        view_func=DownloadAPI.as_view("capture_download", microscope=microscope_obj),
    )

    blueprint.add_url_rule(
        "/<capture_id>/download",
        view_func=DownloadRedirectAPI.as_view(
            "capture_download_redirect", microscope=microscope_obj
        ),
    )

    blueprint.add_url_rule(
        "/<capture_id>/",
        view_func=CaptureAPI.as_view("capture", microscope=microscope_obj),
    )

    blueprint.add_url_rule(
        "/", view_func=ListAPI.as_view("captures", microscope=microscope_obj)
    )
    return blueprint
