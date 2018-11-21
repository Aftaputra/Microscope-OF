#!/usr/bin/env python
"""
TODO: Add proper docstrings
TODO: Implement API route to cleanly shut down server
TODO: Implement microscope function API routes (autofocus etc)
"""

import numpy as np
from importlib import import_module
import time
import datetime
import os

from flask import (
    Flask, render_template, Response, url_for,
    redirect, request, jsonify, send_file, abort,
    make_response)

from flask.views import MethodView
from werkzeug.exceptions import default_exceptions

from openflexure_microscope.api.utilities import parse_payload, get_from_payload, gen, get_bool

from openflexure_microscope import Microscope
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage

import atexit
import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# Create a dummy microscope object, with no hardware attachments
api_microscope = Microscope(None, None)
logging.debug("Created an empty microscope in global.")

# Generate API URI based on version from filename
def uri(suffix, base=None):
    if not base:
        api_ver = os.path.splitext(os.path.basename(__file__))[0]
        base = "/api/{}".format(api_ver)
    uri = base + suffix
    logging.debug("Created app route: {}".format(uri))
    return uri

# Create flask app
app = Flask(__name__)
app.url_map.strict_slashes = False


# Make errors more API friendly

def _handle_http_exception(e):
    return make_response(
        jsonify({
            'status_code': e.code,
            'error': e.name,
            'details': e.description
        }),
        e.code)

for code in default_exceptions:
    app.errorhandler(code)(_handle_http_exception)


# After app starts, but before first request, attach hardware to global microscope
@app.before_first_request
def attach_microscope():
    # Create the microscope object globally (common to all spawned server threads)
    global api_microscope
    logging.debug("First request made. Populating microscope with hardware...")
    api_microscope.attach(
        StreamingCamera(),
        OpenFlexureStage("/dev/ttyUSB0")
    )
    logging.debug("Microscope successfully attached!")


##### WEBAPP ROUTES ######

@app.route('/')
def index():
    """
    API demo app
    """
    return render_template(
        'index_v1.html'
    )

##### API ROUTES ######


# Basic microscope view

class MicroscopeView(MethodView):

    def __init__(self, microscope):
        """
        Create a generic MethodView with a globally available
        microscope object passed as an argument.
        """
        self.microscope = microscope

        MethodView.__init__(self)


class StreamAPI(MicroscopeView):

    def get(self):
        """
        Real-time MJPEG stream from the microscope camera

        .. :quickref: State; Camera stream

        :>header Accept: image/jpeg
        :>header Content-Type: image/jpeg
        :status 200: stream active
        """
        # Restart stream worker thread
        self.microscope.camera.start_worker()

        return Response(
            gen(self.microscope.camera),
            mimetype='multipart/x-mixed-replace; boundary=frame')

app.add_url_rule(
    uri('/stream/'), 
    view_func=StreamAPI.as_view('stream', microscope=api_microscope))


class StateAPI(MicroscopeView):

    def get(self):
        """
        JSON representation of the microscope object.

        .. :quickref: State; Microscope state

        **Example request**:

        .. sourcecode:: http

          GET /state/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "position": {
                "x": 0, 
                "y": 0, 
                "z": 0
            }, 
            "preview_active": false, 
            "record_active": false, 
            "stream_active": true
          }

        :>header Accept: application/json
        :>header Content-Type: application/json
        :status 200: state available
        """
        return jsonify(self.microscope.state)

app.add_url_rule(
    uri('/state/'), 
    view_func=StateAPI.as_view('state', microscope=api_microscope))


class PositionAPI(MicroscopeView):

    def get(self):
        """
        Return current x, y and z positions of the stage.

        .. :quickref: Position; Get current position

        **Example request**:

        .. sourcecode:: http

          GET /position/ HTTP/1.1
          Accept: application/json

        **Example response**:

        .. sourcecode:: http

          HTTP/1.1 200 OK
          Vary: Accept
          Content-Type: application/json

          {
            "x": 0, 
            "y": 0, 
            "z": 0
          }

        :>json int x: x steps
        :>json int y: y steps
        :>json int z: z steps
        """
        return jsonify(self.microscope.state['position'])

    def post(self):
        """
        Set x, y and z positions of the stage.

        .. :quickref: Position; Update current position

        :reqheader Accept: application/json
        :<json boolean absolute: (true) move to absolute position, (false) move by relative amount
        :<json boolean force: allow moving by more than programmed limit
        :<json int x: x steps
        :<json int y: y steps
        :<json int z: z steps

        """
        # Get payload
        state = parse_payload(request)
        logging.debug(state)

        # Construct position array
        position = [0, 0, 0]

        # Handle absolute positioning
        if 'absolute' in state and state['absolute'] is True:
            # Get coordinates from payload
            for axis, key in enumerate(['x', 'y', 'z']):
                if key in state:
                    position[axis] = int(state[key]-self.microscope.stage.position[axis])

        else:
            # Get coordinates from payload
            for axis, key in enumerate(['x', 'y', 'z']):
                if key in state:
                    position[axis] = int(state[key])

        logging.debug(position)

        # Safeguard to prevent moving to an absolute position beyond a fixed limit
        if 'force' not in state or state['force'] is False:  # Allow for override
            # TODO: Make travel_limit a property of the stage or microscope
            # TODO: Make travel_limit a 3-axis list
            travel_limit = 20000 
            for axis, pos in enumerate(position):
                if abs(pos) > travel_limit:
                    # Respond with 400 Bad Request
                    response = {'error': 'Cannot move to absolute position beyond the safeguard limit.'}
                    return jsonify(response), 400

        self.microscope.stage.move_rel(position)

        return jsonify(self.microscope.state['position'])

app.add_url_rule(
    uri('/position/'), 
    view_func=PositionAPI.as_view('position', microscope=api_microscope))


class CaptureListAPI(MicroscopeView):

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
        return jsonify({"error": "not yet implemented"})

    def post(self):
        """
        Create a new image capture.

        .. :quickref: Capture collection; New capture

        **Example request**:

        .. sourcecode:: http

          POST /position/ HTTP/1.1
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

        capture_obj = self.microscope.camera.capture(
            write_to_file=True,  # Always write data to disk when using API
            keep_on_disk=keep_on_disk,
            use_video_port=use_video_port,
            filename=filename,
            resize=resize)

        return jsonify(capture_obj.metadata)

app.add_url_rule(
    uri('/capture/'), 
    view_func=CaptureListAPI.as_view('capture_list', microscope=api_microscope))


class CaptureAPI(MicroscopeView):

    def get(self, capture_id):
        """
        Get JSON representation of a capture

        .. :quickref: Capture; Get capture

        **Example request**:

        .. sourcecode:: http

          GET /capture/d0b2067abbb946f19351e075c5e7cd5b/ HTTP/1.1
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
            'uri': {'metadata': uri('/capture/{}/'.format(capture_id))}
        }

        # If available, also add download link
        if capture_metadata['available']:
            uri_dict['uri']['download'] = uri('/capture/{}/download/{}'.format(capture_obj.id, capture_obj.filename))

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

app.add_url_rule(
    uri('/capture/<capture_id>/'),
    view_func=CaptureAPI.as_view('capture', microscope=api_microscope))


class CaptureDownloadRedirectAPI(MicroscopeView):
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

        return redirect(url_for('capture_download', capture_id=capture_id, filename=capture_obj.filename, as_attachment=as_attachment, thumbnail=thumbnail), code=307)

# Route for shortcut where no filename is specified
app.add_url_rule(
    uri('/capture/<capture_id>/download'),
    view_func=CaptureDownloadRedirectAPI.as_view('capture_download_redirect', microscope=api_microscope))


class CaptureDownloadAPI(MicroscopeView):
    def get(self, capture_id, filename):
        """
        Return image data for a capture.

        Return capture data as an image file with the requested filename. 
        I.e., `/(capture_id)/download/foo.jpeg` will download the image as 
        `foo.jpeg`, regardless of the capture's initially set filename.

        .. :quickref: Capture; Download capture file

        **Example request**:

        .. sourcecode:: http

          GET /capture/d0b2067abbb946f19351e075c5e7cd5b/download/2018-11-20_16-04-17.jpeg HTTP/1.1
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

app.add_url_rule(
    uri('/capture/<capture_id>/download/<filename>'),
    view_func=CaptureDownloadAPI.as_view('capture_download', microscope=api_microscope))

# Automatically clean up microscope at exit
def cleanup():
    global api_microscope
    api_microscope.close()

atexit.register(cleanup)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port="5000", threaded=True, debug=True, use_reloader=False)
