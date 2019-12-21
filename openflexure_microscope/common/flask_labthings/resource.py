from flask.views import MethodView


class Resource(MethodView):
    """Currently identical to MethodView
    """

    def __init__(self, *args, **kwargs):
        MethodView.__init__(self, *args, **kwargs)
