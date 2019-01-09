#!/usr/bin/env python
"""
TODO: Implement API route to cleanly shut down server
TODO: Implement plugin API routes somehow
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

from openflexure_microscope.api.utilities import list_routes

from openflexure_microscope import Microscope, config
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage

import atexit
import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# Create a dummy microscope object, with no hardware attachments
openflexurerc = config.load_config()  # Load default user config
api_microscope = Microscope(None, None, config=openflexurerc)
logging.debug("Created an empty microscope in global.")


# Generate API URI based on version from filename
def uri(suffix, api_version, base=None):
    if not base:
        base = "/api/{}".format(api_version)
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
    global api_microscope, openflexurerc
    logging.debug("First request made. Populating microscope with hardware...")

    logging.debug("Creating camera object...")
    api_camera = StreamingCamera(config=openflexurerc)
    logging.debug("Creating stage object...")
    api_stage = OpenFlexureStage("/dev/ttyUSB0")

    logging.debug("Attaching devices to microscope...")
    api_microscope.attach(
        api_camera,
        api_stage
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
from openflexure_microscope.api.v1 import blueprints

logging.debug("Registering blueprints...")
# Base routes
base_blueprint = blueprints.base.construct_blueprint(api_microscope)
app.register_blueprint(base_blueprint, url_prefix=uri('', 'v1'))

# Stage routes
stage_blueprint = blueprints.stage.construct_blueprint(api_microscope)
app.register_blueprint(stage_blueprint, url_prefix=uri('/stage', 'v1'))

# Camera routes
camera_blueprint = blueprints.camera.construct_blueprint(api_microscope)
app.register_blueprint(camera_blueprint, url_prefix=uri('/camera', 'v1'))

# Pluginroutes
plugin_blueprint = blueprints.plugins.construct_blueprint(api_microscope)
app.register_blueprint(plugin_blueprint, url_prefix=uri('/plugin', 'v1'))

# List all routes
list_routes(app)


# Automatically clean up microscope at exit
def cleanup():
    global api_microscope
    api_microscope.close()

atexit.register(cleanup)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port="5000", threaded=True, debug=True, use_reloader=False)
