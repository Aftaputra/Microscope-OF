import logging
import os
import errno
from werkzeug.exceptions import BadRequest
from flask import url_for, Blueprint


def blueprint_for_module(module_name, api_ver=2, suffix=""):
    return Blueprint(
        blueprint_name_for_module(module_name, api_ver=api_ver, suffix=suffix),
        module_name,
    )


def blueprint_name_for_module(module_name, api_ver=2, suffix=""):
    bp_name = module_name.split(".")[-1]
    return f"v{api_ver}_{bp_name}_blueprint{suffix}"


class JsonResponse:
    def __init__(self, request):
        """
        Object to wrap up simple functionality for parsing a JSON response.
        """
        # Try to load as json
        try:
            self.json = (
                request.get_json()
            )  #: dict: Dictionary representation of request JSON
        # If malformed JSON is passed, make an empty dictionary
        except BadRequest as e:
            logging.error(e)
            self.json = {}

        if self.json is None:
            self.json = {}

        # Store raw response data
        self.data = request.get_data()  #: str: String representation of request data

        if self.data is None:
            self.data = ""

    def param(self, key, default=None, convert=None):
        """
        Check if a key exists in a JSON/dictionary payload, and returns it.

        Args:
            key (str): JSON key to look for
            default: Value to return if no matching key-value pair is found.
            convert: Converter function. By passing a type, the value will be converted to that type. 
                **Use with caution!**
        """
        # If no JSON payload exists, make an empty dictionary
        if not self.json:
            self.json = {}

        if key in self.json:
            val = self.json[key]
        else:
            val = default

        if convert and (val is not None):
            val = convert(val)
        return val


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


def init_default_plugins(plugin_path):
    global _DEFAULT_PLUGIN_INIT
    os.makedirs(os.path.dirname(plugin_path), exist_ok=True)

    if not os.path.exists(plugin_path):  # If user plugins file doesn't exist
        logging.warning("No plugin file found at {}. Creating...".format(plugin_path))
        create_file(plugin_path)

        logging.info("Populating {}...".format(plugin_path))
        with open(plugin_path, "w") as outfile:
            outfile.write(_DEFAULT_PLUGIN_INIT)


_DEFAULT_PLUGIN_INIT = """from openflexure_microscope.plugins.v2.autofocus import autofocus_plugin_v2
from openflexure_microscope.plugins.v2.scan import scan_plugin_v2

__plugins__ = [autofocus_plugin_v2, scan_plugin_v2]"""