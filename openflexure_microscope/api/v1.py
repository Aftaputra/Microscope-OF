#!/usr/bin/env python
"""
TODO: Implement stage control methods
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
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


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
    """Return JSONified microscope state"""
    global microscope

    if request.method == 'POST' or request.method == 'PUT':
        logging.debug("TODO: Move stage.")

    return jsonify(microscope.state['position'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, debug=True, use_reloader=False)
