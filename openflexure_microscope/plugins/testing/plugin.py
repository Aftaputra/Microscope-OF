from openflexure_microscope.plugins import MicroscopePlugin


class Plugin(MicroscopePlugin):
    """
    A set of default plugins
    """

    def identify(self):
        """
        Tests for access to Microscope.camera, and Microscope.stage
        """
        return (self.microscope.camera, self.microscope.stage)
