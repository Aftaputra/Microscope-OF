from flask.views import MethodView
from openflexure_microscope.common.labthings_core.resource import BaseResource


class Resource(MethodView, BaseResource):
    """Currently identical to MethodView
    """

    endpoint = None

    def __init__(self, *args, **kwargs):
        MethodView.__init__(self, *args, **kwargs)
