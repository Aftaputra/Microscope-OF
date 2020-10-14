#!/usr/bin/env python
import atexit
import logging
import logging.handlers
import sys
import time

# Look for debug flag
if "-d" in sys.argv or "--debug" in sys.argv:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO


# Set root logger level
root_log = logging.getLogger()
root_log.setLevel(log_level)


import os
from datetime import datetime

import pkg_resources
from flask import abort, send_file
from flask_cors import CORS, cross_origin
from labthings import create_app
from labthings.extensions import find_extensions

from openflexure_microscope.api.microscope import default_microscope as api_microscope
from openflexure_microscope.api.utilities import init_default_extensions, list_routes
from openflexure_microscope.api.v2 import views
from openflexure_microscope.config import JSONEncoder
from openflexure_microscope.paths import (
    OPENFLEXURE_EXTENSIONS_PATH,
    OPENFLEXURE_VAR_PATH,
    logs_file_path,
)

# Handle logging
access_log = logging.getLogger("werkzeug")
# Block the access logs from propagating up to the root logger
access_log.propagate = False

ROOT_LOGFILE = logs_file_path("openflexure_microscope.log")
ACCESS_LOGFILE = logs_file_path("openflexure_microscope.access.log")

# Basic log format
formatter = logging.Formatter(
    "[%(asctime)s] [%(threadName)s] [%(levelname)s] %(message)s"
)


# Create file handler
fh = logging.handlers.RotatingFileHandler(
    ROOT_LOGFILE, maxBytes=1_000_000, backupCount=5
)
fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)
fh.propagate = False

# Create access log file handler
afh = logging.handlers.RotatingFileHandler(
    ACCESS_LOGFILE, maxBytes=1_000_000, backupCount=5
)
afh.setFormatter(formatter)
afh.setLevel(logging.DEBUG)
afh.propagate = False

# Add file handler to root logger
root_log.addHandler(fh)
access_log.addHandler(afh)

# Log server paths being used
logging.info("Running with data path %s", OPENFLEXURE_VAR_PATH)

logging.info("Creating app")
# Create flask app
app, labthing = create_app(
    __name__,
    prefix="/api/v2",
    title=f"OpenFlexure Microscope {api_microscope.name}",
    description="Test LabThing-based API for OpenFlexure Microscope",
    types=["org.openflexure.microscope"],
    version=pkg_resources.get_distribution("openflexure-microscope-server").version,
    flask_kwargs={"static_url_path": "", "static_folder": "static/dist"},
)

# Enable CORS for some routes outside of LabThings
cors = CORS(app)

# Use custom JSON encoder
labthing.json_encoder = JSONEncoder
app.json_encoder = JSONEncoder

# Attach lab devices
labthing.add_component(api_microscope, "org.openflexure.microscope")

# Attach extensions
if not os.path.isfile(OPENFLEXURE_EXTENSIONS_PATH):
    init_default_extensions(OPENFLEXURE_EXTENSIONS_PATH)
for extension in find_extensions(OPENFLEXURE_EXTENSIONS_PATH):
    labthing.register_extension(extension)

# Attach captures resources
labthing.add_view(views.CaptureList, "/captures")
labthing.add_root_link(views.CaptureList, "captures")

labthing.add_view(views.CaptureView, "/captures/<id>")
labthing.add_view(views.CaptureDownload, "/captures/<id>/download/<filename>")
labthing.add_view(views.CaptureTags, "/captures/<id>/tags")
labthing.add_view(views.CaptureAnnotations, "/captures/<id>/annotations")

# Attach settings and state resources
labthing.add_view(views.SettingsProperty, "/instrument/settings")
labthing.add_root_link(views.SettingsProperty, "instrumentSettings")
labthing.add_view(views.NestedSettingsProperty, "/instrument/settings/<path:route>")
labthing.add_view(views.StateProperty, "/instrument/state")
labthing.add_view(views.NestedStateProperty, "/instrument/state/<path:route>")
labthing.add_root_link(views.StateProperty, "instrumentState")
labthing.add_view(views.ConfigurationProperty, "/instrument/configuration")
labthing.add_view(
    views.NestedConfigurationProperty, "/instrument/configuration/<path:route>"
)
labthing.add_root_link(views.ConfigurationProperty, "instrumentConfiguration")

# Attach stage resources
labthing.add_view(views.StageTypeProperty, "/instrument/stage/type")


# Attach streams resources
labthing.add_view(views.MjpegStream, "/streams/mjpeg")
labthing.add_view(views.SnapshotStream, "/streams/snapshot")

# Attach microscope action resources
labthing.add_view(views.actions.ActionsView, "/actions")
labthing.add_root_link(views.actions.ActionsView, "actions")
for name, action in views.enabled_root_actions().items():
    view_class = action["view_class"]
    rule = action["rule"]
    labthing.add_view(view_class, f"/actions{rule}")


@app.route("/")
def openflexure_ev():
    return app.send_static_file("index.html")


@app.route("/routes")
@cross_origin()
def routes():
    """
    List of all connected API routes
    """
    return list_routes(app)


@app.route("/log")
def err_log():
    """
    Most recent 1mb of log output
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return send_file(
        ROOT_LOGFILE,
        as_attachment=True,
        attachment_filename="openflexure_microscope_{}.log".format(timestamp),
    )


@app.route("/api/v1/", defaults={"path": ""})
@app.route("/api/v1/<path:path>")
def api_v1_catch_all(path):  # pylint: disable=W0613
    abort(410, "API v1 is no longer in use. Please upgrade your client.")


# Automatically clean up microscope at exit
def cleanup():
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

# Start the app
if __name__ == "__main__":
    from labthings import Server

    logging.info("Starting OpenFlexure Microscope Server...")
    server = Server(app)
    server.run(host="0.0.0.0", port=5000, debug=False, zeroconf=True)
