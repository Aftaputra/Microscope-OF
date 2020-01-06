from .spec import update_spec
from .utilities import rupdate


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
