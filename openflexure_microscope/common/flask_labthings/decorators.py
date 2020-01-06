from webargs import flaskparser
from functools import wraps, update_wrapper
from flask import make_response

from openflexure_microscope.common.labthings_core.utilities import rupdate

from .spec import update_spec


def unpack(value):
    """Return a three tuple of data, code, and headers"""
    if not isinstance(value, tuple):
        return value, 200, {}

    try:
        data, code, headers = value
        return data, code, headers
    except ValueError:
        pass

    try:
        data, code = value
        return data, code, {}
    except ValueError:
        pass

    return value, 200, {}


class marshal_with(object):
    def __init__(self, schema):
        """
        :param schema: a dict of whose keys will make up the final
                        serialized response output
        """
        self.schema = schema

    def __call__(self, f):
        # Pass params to call function attribute for external access
        update_spec(f, {"_schema": self.schema})
        # Wrapper function
        @wraps(f)
        def wrapper(*args, **kwargs):
            resp = f(*args, **kwargs)
            if isinstance(resp, tuple):
                data, code, headers = unpack(resp)
                print((data, code, headers))
                return make_response(self.schema.jsonify(data), code, headers)
            else:
                return make_response(self.schema.jsonify(resp))

        return wrapper


class use_args(object):
    def __init__(self, schema, **kwargs):
        """
        Equivalent to webargs.flask_parser.use_args
        """
        self.schema = schema
        self.wrapper = flaskparser.use_args(schema, **kwargs)

    def __call__(self, f):
        # Pass params to call function attribute for external access
        update_spec(f, {"_params": self.schema})
        # Wrapper function
        update_wrapper(self.wrapper, f)
        return self.wrapper(f)


class use_kwargs(use_args):
    def __init__(self, schema, **kwargs):
        """
        Equivalent to webargs.flask_parser.use_kwargs
        """
        kwargs["as_kwargs"] = True
        use_args.__init__(self, schema, **kwargs)


class doc(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, f):
        # Pass params to call function attribute for external access
        update_spec(f, self.kwargs)
        return f


class doc_response(object):
    def __init__(self, code, description, **kwargs):
        self.code = code
        self.description = description
        self.kwargs = kwargs

    def __call__(self, f):
        # Pass params to call function attribute for external access
        f.__apispec__ = f.__dict__.get("__apispec__", {})
        d = {"responses": {self.code: {"description": self.description, **self.kwargs}}}
        rupdate(f.__apispec__, d)
        return f
