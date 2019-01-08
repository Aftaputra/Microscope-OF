from openflexure_microscope.api.utilities import parse_payload, get_from_payload, gen, get_bool
from openflexure_microscope.api.v1.views import MicroscopeView

from flask import Response, Blueprint, jsonify, request, abort, url_for, redirect, send_file

import logging


class ListAPI(MicroscopeView):

    def get(self):
        """
        Get list of image captures.

        .. :quickref: Capture collection; Get collection of captures

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
                            - **metadata** *(string)*: api uri to the capture json representation

        :>header Content-Type: application/json
        :status 200: capture found
        :status 404: no capture found with that id
        """
        include_unavailable = get_bool(request.args.get('include_unavailable'))

        if include_unavailable:
            captures = [image.metadata for image in self.microscope.camera.images]
        else:
            captures = [image.metadata for image in self.microscope.camera.images if image.metadata['available']]

        return jsonify(captures)

    def delete(self):
        """
        Delete all captures (not yet implemented)

        .. :quickref: Capture collection; Delete all captures
        """
        for image in self.microscope.camera.images:
            image.delete()

        captures = [image.metadata for image in self.microscope.camera.images]

        return jsonify(captures)

    def post(self):
        """
        Create a new image capture.

        .. :quickref: Capture collection; New capture

        **Example request**:

        .. sourcecode:: http

          POST /camera/capture HTTP/1.1
          Accept: application/json

          {
            "filename": "myfirstcapture", 
            "keep_on_disk": true, 
            "use_video_port": true,
            "size": {
                "x": 640,
                "y": 480
            }
          }

        :>header Accept: application/json

        :<json string filename: filename of stored capture
        :<json boolean keep_on_disk: keep the capture file on microscope after closing
        :<json boolean use_video_port: capture still image from the video port
        :<json json size:   - **x** *(int)*: x-axis resize
                            - **y** *(int)*: y-axis resize

        :>json boolean available: availability of capture data
        :>json string filename: filename of capture
        :>json string id: unique id of the capture object
        :>json boolean keep_on_disk: keep the capture file on microscope after closing
        :>json boolean locked: file locked for modifications (mostly used for video recording)
        :>json string path: path on pi storage to the capture file, if available
        :>json boolean stream: capture stored in-memory as a BytesIO stream
        :>json json uri: - **download** *(string)*: api uri to the capture file download
                         - **metadata** *(string)*: api uri to the capture json representation

        :<header Content-Type: application/json
        :status 200: capture created
        """
        state = parse_payload(request)
        logging.info(state)

        filename = get_from_payload(state, 'filename', default=None)
        keep_on_disk = bool(get_from_payload(state, 'keep_on_disk', default=True))
        use_video_port = bool(get_from_payload(state, 'use_video_port', default=False))

        resize = get_from_payload(state, 'size', default=None)
        if resize:
            if ('width' in resize) and ('height' in resize):
                resize = (int(resize['width']), int(resize['height']))  # Convert dict to tuple
            else:
                abort(400)

        output = self.microscope.camera.new_image(
            write_to_file=True, 
            keep_on_disk=keep_on_disk, 
            filename=filename)

        self.microscope.camera.capture(
            output,
            use_video_port=use_video_port,
            resize=resize)

        return jsonify(output.metadata)


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
              "filename": "2018-11-16_10-21-53.jpeg", 
              "id": "d0b2067abbb946f19351e075c5e7cd5b", 
              "keep_on_disk": false, 
              "locked": false, 
              "path": "capture/2018-11-16_10-21-53.jpeg", 
              "stream": false, 
              "uri": {
                  "download": "/api/v1/capture/d0b2067abbb946f19351e075c5e7cd5b/download", 
                  "metadata": "/api/v1/capture/d0b2067abbb946f19351e075c5e7cd5b/"
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
                         - **metadata** *(string)*: api uri to the capture json representation

        """
        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        # Get capture metadata
        capture_metadata = capture_obj.metadata

        # TODO: Tidy up adding URI to metadata
        # Add API routes to returned metadata
        uri_dict = {
            'uri': {'metadata': '{}'.format(url_for('.capture', capture_id=capture_obj.id))}
        }

        # If available, also add download link
        if capture_metadata['available']:
            uri_dict['uri']['download'] = '{}download/{}'.format(url_for('.capture', capture_id=capture_obj.id), capture_obj.filename)

        capture_metadata.update(uri_dict)

        return jsonify(capture_metadata)

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
        Modify the metadata of a capture (not yet implemented)

        .. :quickref: Capture; Update capture metadata
        """
        return jsonify({"return": capture_id})


class DownloadRedirectAPI(MicroscopeView):
    def get(self, capture_id):
        """
        Redirect to download the capture under it's currently set filename. 
        I.e., `/(capture_id)/download` will 
        redirect to `/(capture_id)/download/(filename)`.

        Note: This route may be deprecated in the future. Where at all
        possible, please include a filename to download as.

        .. :quickref: Capture; Redirect to download
        """
        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj or not capture_obj.metadata['available']:
            return abort(404)  # 404 Not Found

        as_attachment = get_bool(request.args.get('as_attachment'))
        thumbnail = get_bool(request.args.get('thumbnail'))

        return redirect(url_for('.capture_download', capture_id=capture_id, filename=capture_obj.filename, as_attachment=as_attachment, thumbnail=thumbnail), code=307)


class DownloadAPI(MicroscopeView):
    def get(self, capture_id, filename):
        """
        Return image data for a capture.

        Return capture data as an image file with the requested filename. 
        I.e., `/(capture_id)/download/foo.jpeg` will download the image as 
        `foo.jpeg`, regardless of the capture's initially set filename.

        .. :quickref: Capture; Download capture file

        **Example request**:

        .. sourcecode:: http

          GET /camera/capture/d0b2067abbb946f19351e075c5e7cd5b/download/2018-11-20_16-04-17.jpeg HTTP/1.1
          Accept: image/jpeg

        :>header Accept: image/jpeg
        :query thumbnail: return an image thumbnail e.g. ?thumbnail=true
        :query as_attachment: return the image as an attachment download e.g. ?as_attachment=true

        :>header Content-Type: image/jpeg
        :status 200: capture data found
        :status 404: no capture found with that id
        """
        capture_obj = self.microscope.camera.image_from_id(capture_id)

        if not capture_obj or not capture_obj.metadata['available']:
            return abort(404)  # 404 Not Found

        as_attachment = get_bool(request.args.get('as_attachment'))
        thumbnail = get_bool(request.args.get('thumbnail'))

        # If no filename is specified, redirect to the capture's currently set filename
        if not filename:
            return redirect(url_for('capture_download', capture_id=capture_id, filename=capture_obj.filename, as_attachment=as_attachment, thumbnail=thumbnail), code=307)

        # Download the image data using the requested filename
        if thumbnail:
            img = capture_obj.thumbnail
        else:
            img = capture_obj.data

        return send_file(
            img,
            mimetype='image/jpeg',
            as_attachment=as_attachment,
            attachment_filename=filename)