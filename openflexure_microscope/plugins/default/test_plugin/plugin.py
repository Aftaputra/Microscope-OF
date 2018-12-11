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


class OtherPlugin(MicroscopePlugin):
    """
    An example of a second Microscope plugin, loaded from the same plugin file.
    """
    def do_something(self):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """
        return "Stage plugin parent stage: {}".format(self.microscope.stage)


PLUGINS = {
    'test1': FirstPlugin,
    'test2': OtherPlugin,
}  #: dict: Dictionary describing the plugins. Keys are the names of the plugin's namescape, with a value corresponding to the class of that plugin.