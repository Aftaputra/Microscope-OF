from openflexure_microscope.plugins import MicroscopePlugin


class FirstPlugin(MicroscopePlugin):
    """
    An example Microscope plugin. 
    """
    def run(self):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """

        response = "My parent camera is {}, and my parent stage is {}.".format(self.microscope.camera, self.microscope.stage)
        return response