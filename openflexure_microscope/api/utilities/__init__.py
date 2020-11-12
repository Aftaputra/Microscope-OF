import errno
import logging
import os

from flask import Blueprint, current_app, url_for
from werkzeug.exceptions import BadRequest

from . import gui


def view_class_from_endpoint(endpoint: str):
    return current_app.view_functions[endpoint].view_class


def blueprint_for_module(module_name, api_ver=2, suffix=""):
    return Blueprint(
        blueprint_name_for_module(module_name, api_ver=api_ver, suffix=suffix),
        module_name,
    )


def blueprint_name_for_module(module_name, api_ver=2, suffix=""):
    bp_name = module_name.split(".")[-1]
    return f"v{api_ver}_{bp_name}_blueprint{suffix}"


def gen(camera):
    """Video streaming generator function."""
    while True:
        # the obtained frame is a jpeg
        frame = camera.get_frame()

        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


def get_bool(get_arg):
    """Convert GET request argument string to a Python bool"""
    if get_arg == "true" or get_arg == "True" or get_arg == "1":
        return True
    else:
        return False


def list_routes(app):
    output = {}
    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        endpoint = rule.endpoint
        methods = list(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = {"endpoint": endpoint, "methods": methods}
        output[url] = line

    return output


def create_file(config_path):
    if not os.path.exists(os.path.dirname(config_path)):
        try:
            os.makedirs(os.path.dirname(config_path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def init_default_extensions(extension_dir):
    os.makedirs(extension_dir, exist_ok=True)

    default_ext_path = os.path.join(extension_dir, "defaults.py")

    if not os.path.isfile(default_ext_path):  # If user extensions file doesn't exist
        logging.warning(
            "No extension file found at {}. Creating...".format(extension_dir)
        )
        create_file(default_ext_path)

        logging.info("Populating {}...".format(default_ext_path))
        with open(default_ext_path, "w") as outfile:
            outfile.write(_DEFAULT_EXTENSION_INIT)


_DEFAULT_EXTENSION_INIT = "from openflexure_microscope.api.default_extensions import *"
