from flask.views import MethodView


class Resource(MethodView):
    """Currently identical to MethodView
    """
    endpoint = None

    def __init__(self, *args, **kwargs):
        MethodView.__init__(self, *args, **kwargs)
