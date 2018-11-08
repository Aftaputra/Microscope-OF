#!/usr/bin/env python
"""
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

from openflexure_microscope.api.utilities import parse_payload, gen

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, debug=True, use_reloader=False)
