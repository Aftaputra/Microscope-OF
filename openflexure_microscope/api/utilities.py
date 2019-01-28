import pprint
import logging
import copy
from werkzeug.exceptions import BadRequest

class JsonPayload:
    def __init__(self, request):
        """
        Object to wrap up simple functionality for parsing a JSON response.
        """
        # Try to load as json
        try:
            self.json = request.get_json()  #: dict: Dictionary representation of request JSON
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
            convert: Converter function. By passing a type, the value will be converted to that type. **Use with caution!**
        """
        # If no JSON payload exists, return early
        if not self.json:
            return None

        if key in self.json:
            val = self.json[key]
        else:
            val = default

        if convert:
            val = convert(val)

        return val


def gen(camera):
    """Video streaming generator function."""
    while True:
        # the obtained frame is a jpeg
        frame = camera.get_frame()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def get_bool(get_arg):
    """Convert GET request argument string to a Python bool"""
    if (
        get_arg == 'true' or
        get_arg == 'True' or
        get_arg == '1'):
        return True
    else:
        return False


def list_routes(app):
    """Print available functions."""
    pprint.pprint(list(map(lambda x: repr(x), app.url_map.iter_rules())))
