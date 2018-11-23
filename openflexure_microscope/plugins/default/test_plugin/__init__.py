from openflexure_microscope.plugins import MicroscopePlugin


class FirstPlugin(MicroscopePlugin):
    """
    An example Microscope plugin. 
    """
    def run(self):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """
        print("Parent camera:")
        print(self.camera)

        print("Parent stage:")
        print(self.stage)


class OtherPlugin(MicroscopePlugin):
    """
    An example of a second Microscope plugin, loaded from the same plugin file.
    """
    def run(self):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """
        print("Stage plugin parent stage:")
        print(self.stage)


PLUGINS = {
    'test1': FirstPlugin,
    'test2': OtherPlugin,
}  #: dict: Dictionary describing the plugins. Keys are the names of the plugin's namescape, with a value corresponding to the class of that plugin.