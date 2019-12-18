#!/usr/bin/env python

import time
import atexit
import logging
import sys
import os

from flask import Flask, jsonify, send_file, url_for

from serial import SerialException
from datetime import datetime

from flask_cors import CORS

from openflexure_microscope.api.exceptions import JSONExceptionHandler
from openflexure_microscope.api.utilities import list_routes

from openflexure_microscope.config import (
    settings_file_path,
    JSONEncoder,
    USER_PLUGINS_PATH,
)
from openflexure_microscope.api import v2

from openflexure_microscope.common.labthings.labthing import LabThing
from openflexure_microscope.common.labthings.find import registered_plugins
from openflexure_microscope.common.labthings.plugins import find_plugins

from openflexure_microscope.api.microscope import default_microscope as api_microscope

from openflexure_microscope.api.v2 import views

# Handle logging
is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")

DEFAULT_LOGFILE = settings_file_path("openflexure_microscope.log")

if (__name__ == "__main__") or (not is_gunicorn):
    # If imported, but not by gunicorn
    print("Letting sys handle logs")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
else:
    # Direct standard Python logging to file and console
    root = logging.getLogger()
    error_formatter = logging.Formatter(
        "[%(asctime)s] [%(threadName)s] [%(levelname)s] %(message)s"
    )

    rotating_logfile = logging.handlers.RotatingFileHandler(
        DEFAULT_LOGFILE, maxBytes=1_000_000, backupCount=7
    )

    error_handlers = [rotating_logfile, logging.StreamHandler()]

    for handler in error_handlers:
        handler.setFormatter(error_formatter)
        root.addHandler(handler)

    root.setLevel(logging.getLogger("gunicorn.error").level)


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

# Use custom JSON encoder
app.json_encoder = JSONEncoder

# Enable CORS everywhere
CORS(app, resources=r"*")

# Make errors more API friendly
handler = JSONExceptionHandler(app)

# Build a labthing
labthing = LabThing(app, prefix="/api/v2")
labthing.description = "Test LabThing-based API for OpenFlexure Microscope"
labthing.title = f"OpenFlexure Microscope {api_microscope.name}"

# Attach lab devices
labthing.register_device(api_microscope, "openflexure_microscope")

# Attach plugins
for _plugin in find_plugins(USER_PLUGINS_PATH):
    labthing.register_plugin(_plugin)

# Attach captures resources
labthing.add_resource(views.CaptureList, f"/captures", endpoint="CaptureList")
labthing.register_property(views.CaptureList)
labthing.add_resource(
    views.CaptureResource, f"/captures/<id>", endpoint="CaptureResource"
)
labthing.add_resource(
    views.CaptureDownload,
    f"/captures/<id>/download/<filename>",
    endpoint="CaptureDownload",
)
labthing.add_resource(views.CaptureTags, f"/captures/<id>/tags", endpoint="CaptureTags")
labthing.add_resource(
    views.CaptureMetadata, f"/captures/<id>/metadata", endpoint="CaptureMetadata"
)

# Attach settings and status resources
labthing.add_resource(views.SettingsProperty, f"/settings")
labthing.register_property(views.SettingsProperty)
labthing.add_resource(views.NestedSettingsProperty, "/settings/<path:route>")
labthing.add_resource(views.StatusProperty, "/status")
labthing.register_property(views.StatusProperty)
labthing.add_resource(views.NestedStatusProperty, "/status/<path:route>")

# Attach streams resources
labthing.add_resource(views.MjpegStream, f"/streams/mjpeg")
labthing.register_property(views.MjpegStream)
labthing.add_resource(views.SnapshotStream, f"/streams/snapshot")
labthing.register_property(views.SnapshotStream)

# Attach microscope action resources
for name, action in views.enabled_root_actions().items():
    view_class = action["view_class"]
    rule = action["rule"]
    labthing.add_resource(view_class, "/actions{rule}")
    labthing.register_action(view_class)


@app.route("/routes")
def routes():
    """
    List of all connected API routes

    .. :quickref: Global; Routes

    :>header Accept: application/json
    :>header Content-Type: application/json
    :status 200: stream active
    """
    return jsonify(list_routes(app))


@app.route("/log")
def err_log():
    """
    Most recent 1mb of log output

    .. :quickref: Global; Log

    :>header Accept: application/json
    :>header Content-Type: application/json
    :status 200: stream active
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return send_file(
        DEFAULT_LOGFILE,
        as_attachment=True,
        attachment_filename="openflexure_microscope_{}.log".format(timestamp),
    )


# Automatically clean up microscope at exit
def cleanup():
    global api_microscope
    logging.debug("App teardown started...")
    logging.debug("Settling...")
    time.sleep(0.5)

    # Save config
    logging.debug("Saving config for teardown...")
    api_microscope.save_settings()

    logging.debug("Settling...")
    time.sleep(0.5)

    # Close down the microscope
    logging.debug("Closing devices...")
    api_microscope.close()

    logging.debug("Settling...")
    time.sleep(0.5)

    logging.debug("App teardown complete.")


atexit.register(cleanup)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000", threaded=True, debug=True, use_reloader=False)
