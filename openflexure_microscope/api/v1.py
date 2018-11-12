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
    redirect, request, jsonify, send_file)


import numpy as np

from openflexure_microscope.api.utilities import parse_payload, gen, get_bool

from openflexure_microscope import Microscope
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage

import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# Create the microscope object globally (common to all spawned server threads)
microscope = Microscope(
    StreamingCamera(), 
    OpenFlexureStage("/dev/ttyUSB0")
)

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

# Define API routes

# Basic routes

@app.route(uri('/stream'))
def stream():
    """Video streaming route. Put this in the src attribute of an img tag."""
    global microscope

    # Restart stream worker thread
    microscope.camera.start_worker()

    return Response(
        gen(microscope.camera),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route(uri('/state'))
def state():
    """Return JSONified microscope state"""
    global microscope

    return jsonify(microscope.state)

# Positioning routes

@app.route(uri('/position'), methods=['GET', 'POST', 'PUT'])
def position():
    """Set and get the microscope stage position"""
    global microscope

    if request.method == 'POST' or request.method == 'PUT':
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
                    position[axis] = int(state[key]-microscope.stage.position[axis])

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

        microscope.stage.move_rel(position)

    return jsonify(microscope.state['position'])

# Capture routes
@app.route(uri('/capture'), methods=['GET', 'POST', 'PUT'])
def capture():
    """Return JSONified microscope state"""
    global microscope

    if request.method == 'POST' or request.method == 'PUT':
        state = parse_payload(request)
        print(state)

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

        capture_obj = microscope.camera.capture(
            write_to_file=True,  # Always write data to disk when using API
            keep_on_disk=keep_on_disk,
            use_video_port=use_video_port,
            filename=filename,
            resize=resize)

        return jsonify(capture_obj.metadata)

    else:  # GET requests
        include_unavailable = get_bool(request.args.get('include_unavailable'))

        if include_unavailable:
            captures = [image for image in microscope.camera.images if image.metadata['available']]
        else:
            captures = microscope.camera.images

        metadata_array = [capture.metadata for capture in captures]

        return jsonify(metadata_array)

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, debug=True, use_reloader=False)
