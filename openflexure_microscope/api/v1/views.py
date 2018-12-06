from flask.views import MethodView


class MicroscopeView(MethodView):

    def __init__(self, microscope, **kwargs):
        """
        Create a generic MethodView with a globally available
        microscope object passed as an argument.
        """
        self.microscope = microscope

        MethodView.__init__(self, **kwargs)