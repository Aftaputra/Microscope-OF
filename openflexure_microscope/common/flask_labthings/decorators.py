from webargs import flaskparser
from functools import wraps, update_wrapper
from flask import make_response


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
    def __init__(self, argmap, **kwargs):
        """
        Equivalent to webargs.flask_parser.use_args
        """
        self.argmap = argmap
        self.wrapper = flaskparser.use_args(argmap, **kwargs)

    def __call__(self, f):
        update_wrapper(self.wrapper, f)
        return self.wrapper(f)


class use_kwargs(object):
    def __init__(self, argmap, **kwargs):
        """
        Equivalent to webargs.flask_parser.use_kwargs
        """
        kwargs["as_kwargs"] = True
        self.argmap = argmap
        self.wrapper = flaskparser.use_args(argmap, **kwargs)

    def __call__(self, f):
        update_wrapper(self.wrapper, f)
        return self.wrapper(f)
