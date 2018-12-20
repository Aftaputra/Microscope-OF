from openflexure_microscope.plugins import MicroscopePlugin

from .api import IdentifyAPI, HelloWorldAPI


class Plugin(MicroscopePlugin):
    """
    A set of default plugins
    """

    api_views = {
        '/identify': IdentifyAPI,
        '/hello': HelloWorldAPI,
    }

    def identify(self):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """

        response = "My parent camera is {}, and my parent stage is {}.".format(self.microscope.camera, self.microscope.stage)
        print(response)
        return response

    def hello_world(self):
        """
        Demonstrate passive method
        """

        return "Hello world!"