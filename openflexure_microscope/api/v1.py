#!/usr/bin/env python
"""
TODO: Add proper docstrings
TODO: Bind to port 80
TODO: Reimplement capture methods
TODO: Implement API route to cleanly shut down server
TODO: Implement microscope function API routes (autofocus etc)
"""

from pprint import pprint
from importlib import import_module
import time
import datetime

from flask import (
    Flask, render_template, Response,
    redirect, request, jsonify, send_file, abort,
    make_response)

from flask.views import MethodView

import numpy as np

from openflexure_microscope.api.utilities import parse_payload, gen, get_bool

from openflexure_microscope import Microscope
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage

import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

logging.info("Creating StreamingCamera")
cam = StreamingCamera()
logging.info("Creating stage")
stage = OpenFlexureStage("/dev/ttyUSB0")

# Create the microscope object globally (common to all spawned server threads)
logging.info("Creating microscope")
microscope = Microscope(
    cam, 
    stage
)

logging.info("Creating app")
# Create flask app
app = Flask(__name__)

# Some useful functions
def uri(suffix, base='/api/v1'):
    return base + suffix

# Define front-end routes

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template(
        'index_v1.html'
    )


##### Basic microscope view ######
class MicroscopeView(MethodView):

    def __init__(self, microscope):
        """
        Create a generic MethodView with a globally available
        microscope object passed as an argument.
        """
        self.microscope = microscope
        MethodView.__init__(self)

# Test method
class TestAPI(MicroscopeView):

    def get(self):
        """
        Get method for my cool new MethodView
        """
        return jsonify(self.microscope.state)

    def post(self):
        """
        Post method for my cool new MethodView
        """
        return jsonify(request.get_json())

app.add_url_rule('/test', view_func=TestAPI.as_view('test', microscope=microscope))

# Define API routes

# Basic views


class StreamAPI(MicroscopeView):
    def get(self):
        """
        Video streaming route. Put this in the src attribute of an img tag.
        """
        # Restart stream worker thread
        self.microscope.camera.start_worker()

        return Response(
            gen(self.microscope.camera),
            mimetype='multipart/x-mixed-replace; boundary=frame')

app.add_url_rule(uri('/stream'), view_func=StreamAPI.as_view('stream', microscope=microscope))


class StateAPI(MicroscopeView):
    def get(self):
        """
        Return JSONified microscope state.
        """
        return jsonify(self.microscope.state)

app.add_url_rule(uri('/state'), view_func=StateAPI.as_view('state', microscope=microscope))


# Positioning routes

class PositionAPI(MicroscopeView):

    def get(self):
        """
        Get current position
        """
        return jsonify(self.microscope.state['position'])

    def post(self):
        """
        Update current position
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
        if not 'force' in state or state['force'] is False:  # Allow for override
            # TODO: Make travel_limit a property of the stage or microscope
            # TODO: Make travel_limit a 3-axis list
            travel_limit = 2000 
            for axis, pos in enumerate(position):
                if abs(pos) > travel_limit:
                    # Respond with 400 Bad Request
                    response = {'error': 'Cannot move to absolute position beyond the safeguard limit.'}
                    return jsonify(response), 400

        self.microscope.stage.move_rel(position)

        return jsonify(self.microscope.state['position'])

app.add_url_rule(uri('/position'), view_func=PositionAPI.as_view('position', microscope=microscope))


# Capture routes
class CaptureAPI(MicroscopeView):

    def get(self, capture_id):
        """
        Get list of image captures
        """
        if not capture_id:
            include_unavailable = get_bool(request.args.get('include_unavailable'))

            if include_unavailable:
                captures = [image.metadata for image in self.microscope.camera.images if image.metadata['available']]
            else:
                captures = [image.metadata for image in self.microscope.camera.images]

            return jsonify(captures)
        else:
            print(capture_id)
            capture_obj = microscope.camera.image_from_id(capture_id)

            if not capture_obj:
                return abort(404)  # 404 Not Found

            # Get capture metadata
            capture_metadata = capture_obj.metadata

            # Add API routes to returned metadata
            uri_dict = {
                'uri': {'metadata': uri('/capture/{}/'.format(capture_id))}
            }

            # If available, also add download link
            if capture_metadata['available']:
                uri_dict['uri']['download'] = uri('/capture/{}/download'.format(capture_id))

            capture_metadata.update(uri_dict)

            return jsonify(capture_metadata)

    def delete(self, capture_id):
        return jsonify({"error": "not yet implemented"})

    def post(self):
        """
        Create a new image capture
        """
        state = parse_payload(request)

        if 'filename' in state:
            filename = state['filename']
        else:
            filename = None

        if 'keep_on_disk' in state:
            keep_on_disk = bool(state['keep_on_disk'])
        else:
            keep_on_disk = True

        if 'use_video_port' in state:
            use_video_port = bool(state['use_video_port'])
        else:
            use_video_port = False

        if 'size' in state:
            if 'width' in state['size'] and 'height' in state['size']:
                resize = (state['size']['width'], state['size']['height'])
            else:
                raise Exception("Invalid resize parameters passed. Ensure both width and height are specified.")
        else:
            resize = None

        capture_obj = self.microscope.camera.capture(
            write_to_file=True,  # Always write data to disk when using API
            keep_on_disk=keep_on_disk,
            use_video_port=use_video_port,
            filename=filename,
            resize=resize)

        return jsonify(capture_obj.metadata)

capture_view = CaptureAPI.as_view('capture', microscope=microscope)
app.add_url_rule(uri('/capture/'), defaults={'capture_id': None}, view_func=capture_view, methods=['GET',])
app.add_url_rule(uri('/capture/<capture_id>/'), view_func=capture_view, methods=['GET', 'DELETE'])
app.add_url_rule(uri('/capture/'), view_func=capture_view, methods=['POST',])


# Capture download routes
class CaptureDlAPI(MicroscopeView):
    def get(self, capture_id):
        """
        Return image data for a capture.
        """
        print(capture_id)
        capture_obj = microscope.camera.image_from_id(capture_id)

        if not capture_obj:
            return abort(404)  # 404 Not Found

        as_attachment = get_bool(request.args.get('as_attachment'))
        thumbnail = get_bool(request.args.get('thumbnail'))

        if thumbnail:
            img = capture_obj.thumbnail
        else:
            img = capture_obj.data

        return send_file(
            img,
            mimetype='image/jpeg',
            as_attachment=as_attachment,
            attachment_filename=capture_obj.filename)

app.add_url_rule(uri('/capture/<capture_id>/download/'), view_func=CaptureDlAPI.as_view('capture_download', microscope=microscope))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port="5000", threaded=True, debug=True, use_reloader=False)
