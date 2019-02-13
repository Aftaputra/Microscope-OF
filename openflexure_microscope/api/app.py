#!/usr/bin/env python
"""
TODO: Implement API route to cleanly shut down server
"""

from flask import (
    Flask, render_template)

from flask_cors import CORS

from openflexure_microscope.api.exceptions import JSONExceptionHandler

from openflexure_microscope import Microscope
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_microscope.stage.openflexure import Stage

import atexit
import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# Create a dummy microscope object, with no hardware attachments
api_microscope = Microscope(None, None)


# Generate API URI based on version from filename
def uri(suffix, api_version, base=None):
    if not base:
        base = "/api/{}".format(api_version)
    return_uri = base + suffix
    logging.debug("Created app route: {}".format(return_uri))
    return return_uri


# Create flask app
app = Flask(__name__)
app.url_map.strict_slashes = False

CORS(app, resources=r'/api/*')

# Make errors more API friendly
handler = JSONExceptionHandler(app)


# After app starts, but before first request, attach hardware to global microscope
@app.before_first_request
def attach_microscope():
    # Create the microscope object globally (common to all spawned server threads)
    global api_microscope
    logging.debug("First request made. Populating microscope with hardware...")

    logging.debug("Creating camera object...")
    api_camera = StreamingCamera(config=api_microscope.rc.read())
    
    logging.debug("Creating stage object...")
    api_stage = Stage("/dev/ttyUSB0")

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

# Plugin routes
plugin_blueprint = blueprints.plugins.construct_blueprint(api_microscope)
app.register_blueprint(plugin_blueprint, url_prefix=uri('/plugin', 'v1'))

# Task routes
task_blueprint = blueprints.task.construct_blueprint(api_microscope)
app.register_blueprint(task_blueprint, url_prefix=uri('/task', 'v1'))

# Automatically clean up microscope at exit
def cleanup():
    global api_microscope
    logging.debug("App teardown started...")

    # Save config
    if api_microscope.rc:
        api_microscope.rc.save(backup=True)

    # Update capture DB and metadata files before exiting
    if api_microscope.camera:
        api_microscope.camera.store_captures()

    # Close down the microscope
    api_microscope.close()
    logging.debug("App teardown complete.")


atexit.register(cleanup)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port="5000", threaded=True, debug=True, use_reloader=False)
